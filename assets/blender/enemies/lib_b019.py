"""Armoured eye sphere (newsh9.shp: assembly-newsh9-191 + assembly-newsh9-210) and the grey
shield ship (assembly-newsh9-92), design A (episode 4, lean; D65 hard-surface standard).

THE EYE SPHERE. One flying machine on the sky layer (LAVA RUN, EYESPY), drawn by two rigid
assemblies on one link: the top 72x56 px (newsh9 153/155/157 over 191/193/195) and the lower eye
and lid, 72x28 px (210/212/214). The lower assembly's top row is the top one's row 42: their 14
overlapping rows are pixel-identical, so the whole object is 72 x 70 px, a ball of armour plates
about 6 units across. It is built once, whole, in sphere coordinates (px u right, v down, 72 x 70)
and cut into all nine pieces; the overlap rows carry the same geometry in both assemblies.

  - the ball: a faired ellipsoid on the sprite's own (inner-mask) outline, 30 px high, with a
    plain closed underside 17 px deep; its armour plates are separated by modelled seam grooves;
  - a raised cowl (the sprite's light "swirl" head) on the upper left, split by one seam, and a
    rounded rib (the swirl's tail) curling round under it to the right;
  - a glowing blue light bar arcing down the cowl's right side, set in a dark recessed bezel;
  - a latch rod in a slot on each flank;
  - the eye: a domed lens about 41 x 29 px standing out of the ball's front in a raised bezel,
    a sunk round pupil, raised blue iris vanes radiating from it (the sprite's bright blue
    streaks), and a dark cross frame dividing the lens into four panes.
Colours are the sprite's palette index per region (median, shading and sheen left to the game's
light): armour 6, cowl and rib 11, light bar 132, lens 130, vanes 157, cross 53/97, pupil 1.

THE SHIELD SHIP (assembly-newsh9-92: 92/94 over 244/246, a 48 x 56 px lower half of a 48 x 112
craft whose upper pieces are still sprites). Port of the shared-lib build (lib_b019 helpers copied
in) with an outline shell; its top edge is a seam, cut square.

Outline shells (D51): one sealed copy per object, common.outline_shell(islands="outer", D189), cut
open per piece box (no fill), every _outline node checked non-empty.

Shared builder: assembly-newsh9-191.py (the six top pieces), assembly-newsh9-210.py (the three
lower pieces) and assembly-newsh9-92.py (the ship) each call main(only=[...]) and export only their
own models (public/models/enemies/<piece>.glb + src/render/spriteModels/<piece>.json).
Optional flags after "--": --pieces DIR writes review glbs (wholes + per piece) there, --out X.glb
writes the combined glb there. A normal build writes nothing else.
"""

import json
import math
import os
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector


def _find_repo():
    here = Path(__file__).resolve()
    for p in here.parents:
        if (p / "assets" / "blender" / "common.py").exists() and (p / "package.json").exists():
            return p
    env = os.environ.get("TYRIAN_REPO")
    if env:
        return Path(env)
    raise RuntimeError("assets/blender/common.py not found above " + str(here))


ROOT = _find_repo()
sys.path.insert(0, str(ROOT / "assets" / "blender"))
sys.path.insert(0, str(ROOT / "tools"))
import common  # noqa: E402
import sprite_mask as SM  # noqa: E402

NAME = "assembly-newsh9-191"
HERE = Path(__file__).resolve().parent
OUT = HERE / "assembly-newsh9-191_A.glb"
PX = 1 / 12

# --- the eye sphere: pieces and layout --------------------------------------------------------
TOP = ["newsh9-153", "newsh9-155", "newsh9-157", "newsh9-191", "newsh9-193", "newsh9-195"]
LOW = ["newsh9-210", "newsh9-212", "newsh9-214"]
SW, SH = 72, 70           # the whole sphere in px
LOW_ROW = 42              # the lower assembly's top row in sphere px
# piece centres relative to the sphere's centre (px), as split_assembly wants
SPH_LAYOUT = ([(n, -24 + 24 * (i % 3), -21 + 28 * (i // 3)) for i, n in enumerate(TOP)]
              + [(n, -24 + 24 * i, LOW_ROW + 14 - 35) for i, n in enumerate(LOW)])

# --- the shield ship ---------------------------------------------------------------------------
SHIP = ["newsh9-92", "newsh9-94", "newsh9-244", "newsh9-246"]
SHIP_CENTRE = (159, 5)
SHIP_DX = 8.0             # where the ship sits beside the sphere in the combined glb (units)
SHIP_SX, SHIP_SY = 0.958, 0.982   # the ship plan pulled in onto the inner mask


def load(name):
    return common.load_sprite(ROOT, name)


def merged_sprite(names):
    data = load(names[0])
    for n in names[1:]:
        data["colors"].update(load(n)["colors"])
    return data


def sphere_grid():
    """The whole sphere's palette indices (70 rows of 72, -1 empty), lower assembly over the top."""
    g = [[-1] * SW for _ in range(SH)]
    for names, row0 in ((TOP, 0), (LOW, LOW_ROW)):
        for name in names:
            d = load(name)
            e = next(e for e in d["assemblyLayout"] if e["model"] == name)
            lay = d["assemblyLayout"]
            x_min = min(q["cx"] for q in lay) - 12
            y_min = min(q["cy"] for q in lay) - 14
            x0, y0 = e["cx"] - 12 - x_min, e["cy"] - 14 - y_min + row0
            for r, row in enumerate(d["frames"][0]["pixels"]):
                for c, v in enumerate(row):
                    if v >= 0:
                        g[y0 + r][x0 + c] = v
    return g


# --- sphere coordinates ------------------------------------------------------------------------

OU, OV = 36.0, 35.0       # the ball's plan centre (px)
HT, HB = 24 * PX, 20 * PX  # crown height and underside depth (units)
SPHERE_ANCHOR = 12 * PX     # tyrian_anchor: half the crown height (D181)


def X(u):
    return (u - SW / 2) * PX


def Y(v):
    return (SH / 2 - v) * PX


RIM = []                  # the ball's outline radius (px) per RIM_N angle steps


RIM_N = 360
RIM_HARM, RIM_PAD = 16, 0.12


def fit_rim(grid):
    """The inner mask's outline as a radius per degree round (OU, OV), lightly smoothed."""
    colors = {}
    for n in TOP + LOW:
        colors.update({int(k): tuple(v) for k, v in load(n)["colors"].items()})
    m = SM.masks(grid, colors)
    inner = m["inner"]
    raw = []
    for k in range(RIM_N):
        a = 2 * math.pi * k / RIM_N
        ca, sa = math.cos(a), math.sin(a)
        r = 10.0
        while r < 60:
            u, v = OU + r * ca, OV + r * sa
            iu, iv = int(math.floor(u)), int(math.floor(v))
            if not (0 <= iv < SH and 0 <= iu < SW and inner[iv][iu]):
                break
            r += 0.05
        raw.append(r)
    # A low-pass outline (Fourier terms up to RIM_HARM): the sprite's pixel steps would otherwise
    # ripple the ball into pumpkin lobes; the small pad keeps the edge on the inner mask.
    sm = []
    coef = []
    for h in range(RIM_HARM + 1):
        a = sum(raw[k] * math.cos(2 * math.pi * h * k / RIM_N) for k in range(RIM_N)) * 2 / RIM_N
        b = sum(raw[k] * math.sin(2 * math.pi * h * k / RIM_N) for k in range(RIM_N)) * 2 / RIM_N
        coef.append((a / 2 if h == 0 else a, b))
    for k in range(RIM_N):
        sm.append(sum(a * math.cos(2 * math.pi * h * k / RIM_N) + b * math.sin(2 * math.pi * h * k / RIM_N)
                      for h, (a, b) in enumerate(coef)) + RIM_PAD)
    RIM[:] = sm
    return m


def rim(a):
    t = (a % (2 * math.pi)) / (2 * math.pi) * RIM_N
    i = int(t)
    f = t - i
    return RIM[i % RIM_N] * (1 - f) + RIM[(i + 1) % RIM_N] * f


def rho(u, v):
    du, dv = u - OU, v - OV
    return math.hypot(du, dv) / rim(math.atan2(dv, du))


def zb(u, v):
    """The ball's top surface height over (u, v) (units)."""
    p = min(1.0, rho(u, v))
    return HT * math.sqrt(max(0.0, 1 - p * p))


def normal_of(surface, u, v):
    d = 0.3
    dzdu = (surface(u + d, v) - surface(u - d, v)) / (2 * d)
    dzdv = (surface(u, v + d) - surface(u, v - d)) / (2 * d)
    return Vector((-dzdu / PX, dzdv / PX, 1.0)).normalized()


# --- generic mesh helpers (copied from the old scripts; shared helpers stay untouched) ----------

def _tag(bm, before, mat, smooth):
    for f in set(bm.faces) - before:
        f.material_index = mat
        f.smooth = smooth


def resample(path, step):
    out = [path[0]]
    for a, b in zip(path, path[1:]):
        n = max(1, int(math.ceil(math.hypot(b[0] - a[0], b[1] - a[1]) / step)))
        for i in range(1, n + 1):
            t = i / n
            out.append(tuple(x + (y - x) * t for x, y in zip(a, b)))
    return out


def sweep(bm, path, sides=8, mat=0, smooth=True, surface=zb, step=1.5, power=1.0):
    """A tube lying on a surface along (u, v, lift, half_width_px, half_height) points; rings
    stand square to the surface. A zero ring is a point (a rounded or pointed end). power < 1
    squares the section toward a rounded box."""
    before = set(bm.faces)
    path = resample(path, step)
    norms = [normal_of(surface, u, v) for u, v, _, _, _ in path]
    pts = [Vector((X(u), Y(v), surface(u, v))) + n * lift for (u, v, lift, _, _), n in zip(path, norms)]
    rings = []
    for i, (_, _, _, w, h) in enumerate(path):
        n = norms[i]
        t = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        t -= n * t.dot(n)
        t.normalize()
        side = t.cross(n)
        if w == 0 and h == 0:
            rings.append([bm.verts.new(pts[i])])
            continue
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            ca, sa = math.cos(a), math.sin(a)
            ca, sa = math.copysign(abs(ca) ** power, ca), math.copysign(abs(sa) ** power, sa)
            ring.append(bm.verts.new(pts[i] + side * (w * PX * ca) + n * (h * sa)))
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        if len(r0) == 1 and len(r1) == 1:
            continue
        for k in range(sides):
            j = (k + 1) % sides
            if len(r0) == 1:
                bm.faces.new((r0[0], r1[j], r1[k]))
            elif len(r1) == 1:
                bm.faces.new((r0[k], r0[j], r1[0]))
            else:
                bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
    if len(rings[0]) > 1:
        bm.faces.new(list(reversed(rings[0])))
    if len(rings[-1]) > 1:
        bm.faces.new(rings[-1])
    _tag(bm, before, mat, smooth)


def bridge(bm, r0, r1):
    faces = []
    n = max(len(r0), len(r1))
    for k in range(n):
        j = (k + 1) % n
        if len(r0) == 1:
            faces.append(bm.faces.new((r0[0], r1[k], r1[j])))
        elif len(r1) == 1:
            faces.append(bm.faces.new((r0[k], r1[0], r0[j])))
        else:
            faces.append(bm.faces.new((r0[k], r1[k], r1[j], r0[j])))
    return faces


def to_object(name, bm, mats, coll):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    return obj


def cut_grooves(name, part, grooves, mats, coll):
    """Subtract closed groove tubes from a closed part (exact boolean), one at a time, keeping a
    cut only if the result stays whole (crossing cutters can make the solver drop the part);
    the groove walls take the tube's material."""
    target = to_object(name, part, mats, coll)
    solvers = [i.identifier for i in bpy.types.BooleanModifier.bl_rna.properties["solver"].enum_items]
    for i, tube in enumerate(grooves):
        cutter = to_object(f"{name}_cut{i}", tube, mats, coll)
        cutter.hide_render = True
        mod = target.modifiers.new(f"groove{i}", "BOOLEAN")
        mod.operation = "DIFFERENCE"
        mod.solver = "EXACT" if "EXACT" in solvers else solvers[0]
        mod.object = cutter
        if hasattr(mod, "material_mode"):
            mod.material_mode = "INDEX"
        dg = bpy.context.evaluated_depsgraph_get()
        mesh = bpy.data.meshes.new_from_object(target.evaluated_get(dg))
        target.modifiers.remove(mod)
        if len(mesh.polygons) >= 0.95 * len(target.data.polygons):
            old = target.data
            target.data = mesh
            bpy.data.meshes.remove(old)
        else:
            print(f"cut_grooves: {name} groove {i} skipped (solver dropped the part)")
            bpy.data.meshes.remove(mesh)
        data = cutter.data
        bpy.data.objects.remove(cutter, do_unlink=True)
        bpy.data.meshes.remove(data)
    mesh = target.data
    bpy.data.objects.remove(target, do_unlink=True)
    return mesh


def smoothstep(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


# --- the eye sphere ------------------------------------------------------------------------------

# The eye: lens ellipse (px), the pupil and the lens's bulge out of the ball.
EU, EV, EA, EB = 35.8, 50.6, 20.6, 14.6
PU, PV, PR = 35.6, 51.6, 4.6
LENS_LIFT, LENS_BULGE = 0.05, 0.24
PUPIL_DEPTH = 0.26


def e_of(u, v):
    return ((u - EU) / EA) ** 2 + ((v - EV) / EB) ** 2


def zl(u, v):
    """The lens surface: the ball plus a dome standing out of it."""
    return zb(u, v) + LENS_LIFT + LENS_BULGE * math.sqrt(max(0.0, 1 - e_of(u, v)))


# The cowl ("swirl" head): a superellipse plan raised off the ball with a rounded edge.
CU, CV, CA, CB, CPOW, CH = 28.6, 17.6, 11.6, 8.2, 3.2, 4.6 * PX


def se_pt(a, s, cu, cv, ca, cb, p):
    c, sn = math.cos(a), math.sin(a)
    k = (abs(c) ** p + abs(sn) ** p) ** (-1 / p)
    return cu + ca * s * k * c, cv + cb * s * k * sn


def cowl_profile(s):
    """Height fraction over the cowl's normalized radius: a gently crowned top that rolls over a
    rounded edge (radius about 3 px) down onto the ball."""
    if s <= 0.72:
        return 1.0 - 0.06 * (s / 0.72) ** 2
    t = (s - 0.72) / 0.28
    return 0.94 * math.sqrt(max(0.0, 1 - t * t))


def zc(u, v):
    """Height of the cowl's top over (u, v), for parts lying on it."""
    du, dv = (u - CU) / CA, (v - CV) / CB
    s = (abs(du) ** CPOW + abs(dv) ** CPOW) ** (1 / CPOW)
    return zb(u, v) + CH * cowl_profile(min(s, 1.0)) + 0.01


def build_sphere(sprite, coll):
    tag = "nsh9s"
    mats, slots = [], {}

    def M(key, i, **kw):
        if key not in slots:
            slots[key] = len(mats)
            mats.append(common.palette_material(sprite, i, f"{tag}{key}", **kw))
        return slots[key]

    BALL = M("ball", 7, metallic=0.4, roughness=0.45)
    SEAM = M("seam", 3, metallic=0.4, roughness=0.6)
    COWL = M("cowl", 11, metallic=0.7, roughness=0.32)
    BEZEL = M("bezel", 3, metallic=0.45, roughness=0.55)
    STRIP = M("strip", 132, metallic=1.0, roughness=0.55, emission_strength=0.8)
    ROD = M("rod", 12, metallic=0.85, roughness=0.28)
    SLOT = M("slot", 2, metallic=0.3, roughness=0.7)
    RING = M("ring", 6, metallic=0.6, roughness=0.36)
    LENS = M("lens", 130, metallic=0.15, roughness=0.18, emission_strength=0.3)
    VANE = M("vane", 157, metallic=0.2, roughness=0.25, emission_strength=0.45)
    CROSS_H = M("crossh", 53, metallic=0.4, roughness=0.45)
    CROSS_V = M("crossv", 97, metallic=0.4, roughness=0.45)
    PUPIL = M("pupil", 1, metallic=0.0, roughness=0.9)
    FILL = M("fill", 2, metallic=0.3, roughness=0.7)

    # ---- the ball: rings out from the crown to the rim, then a plain underside ----
    segs, nr = 112, 22
    bb = bmesh.new()

    def ring(p, zf):
        if p == 0:
            return [bb.verts.new((X(OU), Y(OV), zf(0.0)))]
        out = []
        for k in range(segs):
            a = 2 * math.pi * k / segs
            r = rim(a) * p
            out.append(bb.verts.new((X(OU + r * math.cos(a)), Y(OV + r * math.sin(a)), zf(p))))
        return out

    ps = [math.sin(0.5 * math.pi * i / nr) ** 0.9 for i in range(nr + 1)]
    top = [ring(p, lambda p: HT * math.sqrt(max(0.0, 1 - p * p))) for p in ps]
    under = [top[-1]] + [ring(p, lambda p: -HB * math.sqrt(max(0.0, 1 - p * p)))
                         for p in (0.97, 0.88, 0.72, 0.5, 0.0)]
    for r0, r1 in zip(top, top[1:]):
        for f in bridge(bb, r0, r1):
            f.material_index, f.smooth = BALL, True
    for r0, r1 in zip(under, under[1:]):
        for f in bridge(bb, r0, r1):
            f.material_index, f.smooth = BALL, True   # one armour grey all round: no dark skirt

    def groove(points, surface=zb, w=0.62, h=0.09, mat=SEAM):
        t = bmesh.new()
        sweep(t, [(u, v, 0.0, w, h) for u, v in points], sides=6, mat=mat, surface=surface, step=0.8,
              smooth=False)
        return t

    # Armour seams traced from the sprite's dark lines (px).
    seams = [
        [(23.6, 2.6), (25.4, 6.0), (27.0, 8.6)],                       # top left plate edge
        [(37.2, 1.4), (35.8, 5.0), (34.6, 8.8)],                       # top centre
        [(41.0, 2.8), (44.0, 6.4), (48.0, 9.6), (50.0, 13.0)],         # top right, round to the flank
        [(49.6, 13.4), (54.0, 13.6), (59.0, 13.4), (65.5, 13.6)],      # right flank, upper
        [(49.6, 13.4), (49.4, 20.0), (49.4, 27.0), (49.8, 35.0)],      # right flank, vertical
        [(50.4, 26.0), (54.0, 25.8), (58.0, 26.4), (63.6, 27.4)],      # right flank, middle
        [(50.0, 35.2), (54.0, 35.6), (57.4, 36.6)],                    # right, above the eye
        [(1.6, 20.6), (5.0, 22.2), (9.0, 23.6), (15.6, 24.6)],         # left flank, upper
        [(1.2, 36.0), (4.0, 37.0)],                                    # left flank, lower stub
        [(15.0, 28.6), (20.0, 28.4), (25.0, 28.4), (30.0, 28.8)],      # under the cowl
        [(12.0, 43.6), (14.0, 40.0), (16.2, 36.8), (21.0, 35.4)],      # round the eye, upper left
        [(51.0, 37.4), (54.4, 40.0), (56.2, 43.0)],                    # round the eye, upper right
    ]
    bm = bmesh.new()
    bm.from_mesh(cut_grooves(NAME + "_ball", bb, [groove(p) for p in seams], mats, coll))

    # ---- the cowl: a raised plate on the upper left, split by one seam ----
    bc = bmesh.new()
    S, nrc = 64, 10
    rings_c = []
    ss = [0.0, 0.25, 0.5, 0.66, 0.74, 0.82, 0.88, 0.93, 0.965, 0.99, 1.0]
    for s in ss:
        if s == 0:
            rings_c.append([bc.verts.new((X(CU), Y(CV), zb(CU, CV) + CH))])
            continue
        rr = []
        for k in range(S):
            a = 2 * math.pi * k / S
            u, v = se_pt(a, s, CU, CV, CA, CB, CPOW)
            z = zb(u, v) + CH * cowl_profile(s) - (0.04 if s == 1.0 else 0.0)
            rr.append(bc.verts.new((X(u), Y(v), z)))
        rings_c.append(rr)
    floor = [bc.verts.new((X(CU), Y(CV), zb(CU, CV) - 0.08))]
    for r0, r1 in zip(rings_c, rings_c[1:]):
        for f in bridge(bc, r0, r1):
            f.material_index, f.smooth = COWL, True
    for f in bridge(bc, rings_c[-1], floor):
        f.material_index, f.smooth = COWL, False
    cowl_seam = [(29.6, 9.0), (29.0, 13.0), (29.4, 17.0), (30.6, 21.0), (31.6, 26.6)]
    bm.from_mesh(cut_grooves(NAME + "_cowl", bc, [groove(cowl_seam, surface=lambda u, v: zc(u, v) - 0.01,
                                                         w=0.55, h=0.07)], mats, coll))

    # ---- the swirl's tail: a rounded rib curling under the cowl and up to the light bar ----
    tail = [(19.0, 36.2, 0.0, 0.0, 0.0), (21.0, 35.8, 0.0, 1.8, 0.07), (25.0, 35.0, 0.0, 2.4, 0.11),
            (30.0, 33.6, 0.0, 2.8, 0.13), (35.0, 32.0, 0.0, 3.0, 0.14), (39.0, 30.0, 0.0, 2.9, 0.14),
            (41.4, 27.4, 0.0, 2.5, 0.13), (42.4, 25.0, 0.0, 2.0, 0.11), (42.6, 23.4, 0.0, 0.0, 0.0)]
    sweep(bm, tail, sides=12, mat=COWL, power=0.55, step=1.0)

    # ---- the light bar, in a dark recessed bezel ----
    bar = [(38.2, 10.8), (41.0, 12.2), (43.6, 14.6), (45.4, 17.6), (46.2, 21.0), (46.2, 24.0), (46.0, 25.6)]
    widths = [2.4, 3.0, 3.0, 2.9, 2.7, 2.6, 2.2]
    sweep(bm, [(bar[0][0] - 0.8, bar[0][1] - 0.4, 0.0, 0.0, 0.0)]
          + [(u, v, 0.0, w + 0.9, 0.05) for (u, v), w in zip(bar, widths)]
          + [(bar[-1][0], bar[-1][1] + 1.2, 0.0, 0.0, 0.0)], sides=10, mat=BEZEL, power=0.6, step=1.0)
    sweep(bm, [(bar[0][0] - 0.4, bar[0][1] - 0.2, 0.04, 0.0, 0.0)]
          + [(u, v, 0.06, w, 0.16) for (u, v), w in zip(bar, widths)]
          + [(bar[-1][0], bar[-1][1] + 0.9, 0.05, 0.0, 0.0)], sides=12, mat=STRIP, power=0.7, step=1.0)

    # ---- latch rods in slots on each flank ----
    for path in ([(9.4, 30.6), (11.2, 34.4), (13.4, 39.2)], [(61.6, 31.2), (59.8, 34.6), (57.8, 38.4)]):
        (u0, v0), _, (u1, v1) = path
        dx = 1.2 if u0 < 36 else -1.2
        sweep(bm, [(u0 - dx, v0 + 0.2, -0.03, 0.0, 0.0)] + [(u - dx * 0.7, v + 0.3, -0.03, 1.7, 0.05) for u, v in path]
              + [(u1 - dx * 0.4, v1 + 1.0, -0.03, 0.0, 0.0)], sides=8, mat=SLOT, power=0.6)
        sweep(bm, [(u0, v0, 0.05, 0.0, 0.0)] + [(u, v, 0.07, 1.0, 0.075) for u, v in path]
              + [(u1 + (u1 - u0) * 0.08, v1 + 0.6, 0.05, 0.0, 0.0)], sides=8, mat=ROD)
        for u, v in (path[0], path[2]):   # the rod's two clamp blocks
            sweep(bm, [(u - 0.9, v, 0.02, 1.3, 0.11), (u + 0.9, v, 0.02, 1.3, 0.11)], sides=8, mat=RING,
                  power=0.5, step=2.0)

    # ---- the eye ----
    E = 72
    be = bmesh.new()

    def eye_pt(k, s):
        """Point s of the way from the pupil's rim to the lens's rim, at angle step k."""
        a = 2 * math.pi * k / E
        iu, iv = PU + PR * math.cos(a), PV + PR * math.sin(a)
        ou, ov = EU + EA * math.cos(a), EV + EB * math.sin(a)
        return iu + (ou - iu) * s, iv + (ov - iv) * s

    def ring_at(uvs, fn):
        return [be.verts.new((X(u), Y(v), fn(u, v))) for u, v in uvs]

    sl = [0.0, 0.08, 0.2, 0.34, 0.48, 0.62, 0.75, 0.86, 0.94, 0.985, 1.0]
    lens = [ring_at([eye_pt(k, s) for k in range(E)], zl) for s in sl]
    for r0, r1 in zip(lens, lens[1:]):
        for f in bridge(be, r0, r1):
            f.material_index, f.smooth = LENS, True
    # the lens's rim wall down into the ball, and a floor under it all (closed solid)
    wall = ring_at([eye_pt(k, 1.0) for k in range(E)], lambda u, v: zb(u, v) - 0.08)
    for f in bridge(be, lens[-1], wall):
        f.material_index, f.smooth = BEZEL, False
    flo = [be.verts.new((X(EU), Y(EV), zb(EU, EV) - 0.1))]
    for f in bridge(be, wall, flo):
        f.material_index, f.smooth = FILL, False
    # the pupil: a round-bottomed port sunk into the lens
    bowl = [lens[0]]
    for t, d in ((0.82, 0.16), (0.45, PUPIL_DEPTH - 0.02)):
        bowl.append(ring_at([(PU + PR * t * math.cos(2 * math.pi * k / E), PV + PR * t * math.sin(2 * math.pi * k / E))
                             for k in range(E)], lambda u, v, d=d: zl(u, v) - d))
    bowl.append([be.verts.new((X(PU), Y(PV), zl(PU, PV) - PUPIL_DEPTH))])
    for r0, r1 in zip(bowl, bowl[1:]):
        for f in bridge(be, r0, r1):
            f.material_index, f.smooth = PUPIL, True
    bm.from_mesh(_bm_to_mesh(be))

    # the bezel: a rounded ring round the lens, standing about 2 px proud of the ball
    bz = []
    for k in range(E + 1):
        a = 2 * math.pi * k / E
        u, v = EU + (EA + 0.9) * math.cos(a), EV + (EB + 0.9) * math.sin(a)
        bz.append((u, v, 0.03, 1.35, 0.13))
    sweep(bm, bz[:E // 2 + 1], sides=10, mat=RING, step=1.2, power=0.75)
    sweep(bm, bz[E // 2:], sides=10, mat=RING, step=1.2, power=0.75)

    # the iris vanes: raised blue ribs radiating from the pupil
    NV = 22
    for i in range(NV):
        a = 2 * math.pi * (i + 0.3) / NV
        pts = []
        for s, w, h in ((0.07, 0.0, 0.0), (0.12, 0.55, 0.035), (0.35, 0.65, 0.04), (0.6, 0.55, 0.035),
                        (0.76, 0.0, 0.0)):
            u = PU + PR * math.cos(a) + (EU + EA * math.cos(a) - PU - PR * math.cos(a)) * s
            v = PV + PR * math.sin(a) + (EV + EB * math.sin(a) - PV - PR * math.sin(a)) * s
            pts.append((u, v, 0.005, w, h))
        sweep(bm, pts, sides=6, mat=VANE, surface=zl, step=1.5)

    # the cross frame: a dark rib down and one across the lens, stopping at the pupil
    def rib(points, mat):
        sweep(bm, [(u, v, 0.01, w, h) for u, v, w, h in points], sides=8, mat=mat, surface=zl, step=0.8,
              power=0.6)
    top_v = EV - EB + 0.6
    rib([(36.5, top_v, 0.0, 0.0), (36.5, top_v + 0.6, 0.65, 0.05), (36.5, PV - PR - 0.4, 0.65, 0.05),
         (36.5, PV - PR + 0.2, 0.0, 0.0)], CROSS_V)
    rib([(36.5, PV + PR - 0.2, 0.0, 0.0), (36.5, PV + PR + 0.4, 0.65, 0.05), (36.5, EV + EB - 1.0, 0.65, 0.05),
         (36.5, EV + EB - 0.4, 0.0, 0.0)], CROSS_V)
    rib([(EU - EA + 0.7, 51.6, 0.0, 0.0), (EU - EA + 1.3, 51.6, 0.65, 0.05), (PU - PR - 0.4, 51.6, 0.65, 0.05),
         (PU - PR + 0.2, 51.6, 0.0, 0.0)], CROSS_H)
    rib([(PU + PR - 0.2, 50.8, 0.0, 0.0), (PU + PR + 0.4, 50.8, 0.65, 0.05), (EU + EA - 1.3, 50.8, 0.65, 0.05),
         (EU + EA - 0.7, 50.8, 0.0, 0.0)], CROSS_H)

    obj = to_object(NAME, bm, mats, coll)
    return obj, slots


def _bm_to_mesh(b):
    me = bpy.data.meshes.new("tmp")
    b.to_mesh(me)
    b.free()
    return me


# --- the shield ship (port of assembly-newsh9-92.py and its lib_b019 helpers) --------------------

class Grid:
    def __init__(self, w, h):
        self.w, self.h = w, h

    def x(self, c):
        return (c - self.w / 2) * PX

    def y(self, r):
        return (self.h / 2 - r) * PX


def _se(a, power):
    c, s = math.cos(a), math.sin(a)
    return math.copysign(abs(c) ** power, c), math.copysign(abs(s) ** power, s)


def _join_rings(bm, rings, sides, mat, cap_start=True, cap_end=True):
    faces = []
    for r0, r1 in zip(rings, rings[1:]):
        if len(r0) == 1 and len(r1) == 1:
            continue
        for i in range(sides):
            j = (i + 1) % sides
            if len(r0) == 1:
                f = (r0[0], r1[j], r1[i])
            elif len(r1) == 1:
                f = (r0[i], r0[j], r1[0])
            else:
                f = (r0[i], r0[j], r1[j], r1[i])
            faces.append(bm.faces.new(f))
    if cap_start and len(rings[0]) > 1:
        faces.append(bm.faces.new(list(reversed(rings[0]))))
    if cap_end and len(rings[-1]) > 1:
        faces.append(bm.faces.new(rings[-1]))
    for f in faces:
        f.material_index = mat
    return faces


def ltube(bm, g, points, sides=10, mat=0, power=1.0, cap_start=True, cap_end=True, smooth=True):
    pos = [Vector((g.x(c), g.y(r))) for c, r, *_ in points]
    rings = []
    for i, (c, r, hw, hh, z) in enumerate(points):
        p = pos[i]
        if hw == 0 and hh == 0:
            rings.append([bm.verts.new((p.x, p.y, z))])
            continue
        d = pos[min(i + 1, len(pos) - 1)] - pos[max(i - 1, 0)]
        d.normalize()
        n = Vector((-d.y, d.x))
        ring = []
        for k in range(sides):
            u, v = _se(2 * math.pi * (k + 0.5) / sides, power)
            q = p + n * (hw * PX * u)
            ring.append(bm.verts.new((q.x, q.y, z + hh * v)))
        rings.append(ring)
    faces = _join_rings(bm, rings, sides, mat, cap_start, cap_end)
    for f in faces:
        f.smooth = smooth
    return faces


def lslab(bm, g, outline, z0, z1, mat=0, bevel=0.0, smooth=False):
    pts = [Vector((g.x(c), g.y(r))) for c, r in outline]
    area = sum(a.x * b.y - b.x * a.y for a, b in zip(pts, pts[1:] + pts[:1]))
    if area < 0:
        pts.reverse()
    cen = sum(pts, Vector((0, 0))) / len(pts)
    bottom = [bm.verts.new((p.x, p.y, z0)) for p in pts]
    top = []
    for p in pts:
        q = p
        if bevel:
            d = cen - p
            k = min(bevel * PX / (d.length or 1), 0.9)
            q = p + d * k
        top.append(bm.verts.new((q.x, q.y, z1)))
    faces = [bm.faces.new(top), bm.faces.new(list(reversed(bottom)))]
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        faces.append(bm.faces.new((bottom[i], bottom[j], top[j], top[i])))
    for f in faces:
        f.material_index = mat
        f.smooth = smooth
    return faces


def lbox(bm, g, c0, r0, c1, r1, z0, z1, mat=0):
    return lslab(bm, g, [(c0, r0), (c1, r0), (c1, r1), (c0, r1)], z0, z1, mat=mat)


def mirror_all(bm, axis_x=0.0):
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    dup = bmesh.ops.duplicate(bm, geom=geom)["geom"]
    for v in (e for e in dup if isinstance(e, bmesh.types.BMVert)):
        v.co.x = 2 * axis_x - v.co.x
    bmesh.ops.reverse_faces(bm, faces=[e for e in dup if isinstance(e, bmesh.types.BMFace)])


G = Grid(48, 56)
AXIS = 24
DOME, FALL, BELLY = 6.5, 10.0, 0.5
CAB = 2.5 / 12
SMOOTH = [(-0.5, 24.0), (34.5, 24.0), (36.5, 23.0), (39.5, 22.0), (40.5, 21.85), (42.5, 20.2), (44.5, 19.0),
          (46.5, 16.9), (48.5, 14.9), (50.5, 12.9), (51.5, 11.85), (52.5, 9.85), (53.5, 8.85), (54.5, 6.6),
          (55.5, 4.0), (56.0, 0.0)]
HULL = ([(0.0, 24.1, 0.14), (16.5, 24.1, 0.14), (34.0, 24.1, 0.14)]
        + [(r, w + 0.2, 0.04 + 0.1 * w / 24) for r, w in SMOOTH[2:-1]] + [(55.9, 2.5, 0.05)])
GLASS_OUTLINE = [(0.8, 0.0), (9.6, 0.0), (11, 1.2), (11, 15), (9, 15), (7, 14), (5, 12), (4, 10), (3, 8),
                 (2, 5), (1, 4)]


def densify(points, step):
    out = [points[0]]
    for a, b in zip(points, points[1:]):
        n = max(1, int(-(-(b[0] - a[0]) // step)))
        for k in range(1, n + 1):
            t = k / n
            out.append(tuple(x + (y - x) * t for x, y in zip(a, b)))
    return out


def _outline_dist(c, r):
    x = abs(c - AXIS)
    pts = [(w, row) for row, w in SMOOTH]
    best = 1e9
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        dx, dy = x1 - x0, y1 - y0
        t = max(0.0, min(1.0, ((x - x0) * dx + (r - y0) * dy) / (dx * dx + dy * dy)))
        best = min(best, ((x - x0 - t * dx) ** 2 + (r - y0 - t * dy) ** 2) ** 0.5)
    if r > 56.0:
        return 0.0
    w = pts[0][0]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if y0 <= r <= y1 and y1 > y0:
            w = x0 + (x1 - x0) * (r - y0) / (y1 - y0)
            break
    # the top edge is a seam onto the craft's upper half: the dome does not fall away there
    return best if x < w else 0.0


def ship_dome(bm):
    for v in bm.verts:
        c, r = v.co.x * 12 + G.w / 2, G.h / 2 - v.co.y * 12
        t = min(_outline_dist(c, r) / FALL, 1.0)
        lift = DOME * (1 - (1 - t) ** 2) / 12
        v.co.z += lift if v.co.z > -1e-4 else -BELLY * lift


def fine_top(bm, faces, cuts=2):
    tris = bmesh.ops.triangulate(bm, faces=[faces[0]])["faces"]
    edges = list({e for f in tris for e in f.edges})
    res = bmesh.ops.subdivide_edges(bm, edges=edges, cuts=cuts, use_grid_fill=True)
    for f in res["geom"]:
        if isinstance(f, bmesh.types.BMFace):
            f.smooth = True
    for f in tris:
        if f.is_valid:
            f.smooth = True


def ship_pixels():
    px = {}
    for piece in SHIP:
        d = load(piece)
        e = next(e for e in d["assemblyLayout"] if e["model"] == piece)
        x0, y0 = e["cx"] - 12 - (SHIP_CENTRE[0] - 24), e["cy"] - 14 - (SHIP_CENTRE[1] - 28)
        for r, row in enumerate(d["frames"][0]["pixels"]):
            for c, v in enumerate(row):
                if v >= 0:
                    px[(x0 + c, y0 + r)] = v
    return px


def build_ship(sprite, coll):
    tag = "nsh9a"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(5, metallic=0.7, roughness=0.3),
        pal(4, metallic=0.5, roughness=0.4),
        pal(7, metallic=0.55, roughness=0.35),
        pal(2, metallic=0.2, roughness=0.8),
        common.palette_material(sprite, 149, tag + "glass", metallic=0.05, roughness=0.1, emission_strength=1.2),
        pal(148, metallic=0.2, roughness=0.3),
        pal(151, metallic=0.05, roughness=0.1, emission_strength=1.5),
        common.palette_material(sprite, 151, tag + "lamp", emission_strength=2.0),
        common.palette_material(sprite, 151, tag + "chan", emission_strength=3.0,
                                frames={130: 156, 132: 156, 282: 153, 284: 153}),
        pal(9, metallic=0.6, roughness=0.3),
        pal(5, metallic=0.7, roughness=0.3),
        common.palette_material(sprite, 149, tag + "glass", metallic=0.05, roughness=0.1, emission_strength=1.2),
        common.palette_material(sprite, 144, tag + "chand", emission_strength=1.0,
                                frames={130: 149, 132: 149, 282: 146, 284: 146}),
        pal(3, metallic=0.4, roughness=0.5),
        common.palette_material(sprite, 157, tag + "core", emission_strength=3.0),
        pal(10, metallic=0.55, roughness=0.3),
    ]
    (HULL_M, KEEL, LIGHT, DARK, GLASS, GRID, PANE, LAMP, CHANNEL, BRIGHT, POD, GLASS_R, CHAN_DARK, FLANK,
     CELL, RIM_R) = range(16)
    extra = {}

    def mat_for(key, make):
        if key not in extra:
            mats.append(make())
            extra[key] = len(mats) - 1
        return extra[key]

    def channel(i):
        i = min((144, 146, 148, 150, 152, 154), key=lambda q: abs(q - i))
        return mat_for(("c", i), lambda: common.palette_material(
            sprite, i, tag + "chan", emission_strength=2.5,
            frames={130: min(i + 5, 159), 132: min(i + 5, 159), 282: i + 2, 284: i + 2}))

    def lamp(i):
        i = min((148, 150, 152, 154, 156, 158), key=lambda q: abs(q - i))
        return mat_for(("l", i), lambda: common.palette_material(
            sprite, i, tag + "lamp", emission_strength=2.0 if i < 154 else 3.0))
    bm = bmesh.new()
    fine_top(bm, lslab(bm, G, [(0.4, 0.0), (12, 0.0), (12, 20.5), (8, 20.5), (5, 18.5), (2, 15.5),
                               (0.4, 13)], -0.05, 0.3, mat=POD, bevel=0.8))
    fine_top(bm, lslab(bm, G, GLASS_OUTLINE, 0.26, 0.33, mat=GLASS, bevel=0.3))
    ltube(bm, G, [(1.2, 14.4, 0.0, 0.0, 0.28), (2.2, 15.6, 0.7, 0.04, 0.285), (5, 18.4, 0.7, 0.04, 0.29),
                  (8, 20.3, 0.7, 0.04, 0.29), (12.5, 20.6, 0.7, 0.04, 0.25), (13.4, 20.6, 0.0, 0.0, 0.24)],
          sides=6, mat=BRIGHT)
    for r in (31, 36):
        lbox(bm, G, 12.6, r, 19.6, r + 1, 0.19, 0.235, mat=LIGHT)
    lbox(bm, G, 12.2, 27, 16, 30.6, 0.2, 0.232, mat=DARK)
    lbox(bm, G, 12.5, 0.0, 17.5, 2.6, 0.18 + CAB, 0.225 + CAB, mat=KEEL)
    mirror_all(bm, G.x(AXIS))
    px = ship_pixels()
    ltube(bm, G, [(AXIS, r, w, h, 0.0) for r, w, h in HULL[:3] + densify(HULL[2:], 2.5)[1:]], sides=24,
          mat=HULL_M, power=0.6)
    keel = [(16.6, 11.6, 0.2), (17.6, 12.0, 0.22), (46, 12.0, 0.22), (48, 11.6, 0.21), (50, 10.8, 0.2),
            (51.5, 9.8, 0.185), (53, 8.0, 0.165), (54.4, 5.6, 0.13), (55.3, 2.5, 0.07)]
    ltube(bm, G, [(AXIS, r, w, h, 0.0) for r, w, h in densify(keel, 3)], sides=16, mat=KEEL, power=0.5)
    H, HD = 4.6 / 12, 0.02 + 0.7 / 12

    def chan_h(r):
        if r <= 39.0 or r >= 49.0:
            return H
        if 41.5 <= r <= 46.5:
            return HD
        t = (r - 39.0) / 2.5 if r < 41.5 else (49.0 - r) / 2.5
        return HD + (H - HD) * (0.5 + 0.5 * math.cos(math.pi * t))
    rows = [28.6, 29.2] + [float(r) for r in range(30, 52)] + [51.5]
    pts = [(AXIS, 28.05, 0.0, 0.0, 0.2), (AXIS, 28.6, 3.0, H * 0.7, 0.2)]
    pts += [(AXIS, r, 4.0, chan_h(r), 0.2) for r in rows[1:]]
    pts += [(AXIS, 53.3, 3.9, H * 0.6, 0.2), (AXIS, 54.6, 3.6, H * 0.4, 0.15), (AXIS, 55.3, 2.5, H * 0.25, 0.1)]
    for f in ltube(bm, G, pts, sides=16, mat=CHANNEL, power=0.85):
        cen = f.calc_center_median()
        row = min(54, max(28, int((G.h / 2 - cen.y * 12) // 1)))
        f.material_index = channel(px.get((24, row), 151))
    lh, lz = 1.25 / 12, 0.22 + 0.8 / 12
    for r in (19.5, 24.5):
        for f in ltube(bm, G, [(20.0, r, 1.2, lh * 0.55, lz), (20.6, r, 1.5, lh * 0.9, lz)]
                       + [(float(c), r, 1.5, lh, lz) for c in range(21, 28)]
                       + [(27.4, r, 1.5, lh * 0.9, lz), (28.0, r, 1.2, lh * 0.55, lz)], sides=8, mat=LAMP):
            cen = f.calc_center_median()
            col = min(27, max(20, int((cen.x * 12 + G.w / 2) // 1)))
            row = min(int(r) + 1, max(int(r) - 1, int((G.h / 2 - cen.y * 12) // 1)))
            f.material_index = lamp(px.get((col, row), 151))
        lbox(bm, G, 19.5, r + 1.4, 28.5, r + 2.2, 0.19, 0.24, mat=LIGHT)
    lslab(bm, G, [(11, 0.0), (37, 0.0), (37, 16.5), (35.5, 17.5), (12.5, 17.5), (11, 16.5)],
          -0.06, 0.2 + CAB, mat=KEEL, bevel=0.4)
    lbox(bm, G, 18, 0.0, 30, 2.6, 0.18 + CAB, 0.24 + CAB, mat=HULL_M)
    rws, cols = ((3.6, 8), (8.6, 10), (10.6, 12), (12.6, 16)), ((15.2, 22), (22.6, 26), (26.6, 30), (30.6, 33.8))
    for r0, r1 in rws:
        for c0, c1 in cols:
            lbox(bm, G, c0, r0, c1, r1, 0.18 + CAB, 0.205 + CAB, mat=PANE)
    mz0, mz1 = 0.18 + CAB, 0.25 + CAB
    for c0, c1 in ((15, 15.2), (22, 22.6), (26, 26.6), (30, 30.6), (33.8, 34)):
        lbox(bm, G, c0, 2.6, c1, 16, mz0, mz1, mat=GRID)
    for r0, r1 in ((2.6, 3.6), (8, 8.6), (10, 10.6), (12, 12.6)):
        for c0, c1 in cols:
            lbox(bm, G, c0, r0, c1, r1, mz0, mz1, mat=GRID)
    lbox(bm, G, 13.6, 2.6, 15, 16, 0.18 + CAB, 0.25 + CAB, mat=KEEL)
    lbox(bm, G, 34, 2.6, 35.4, 16, 0.18 + CAB, 0.25 + CAB, mat=KEEL)
    lbox(bm, G, 13.6, 16, 35.4, 17.2, 0.18 + CAB, 0.25 + CAB, mat=LIGHT)
    ship_dome(bm)
    # Pull the plan in onto the sprite's inner mask (D74: the game draws the ink border round the
    # model): about 1 px at the flanks and the tip, the top seam row stays where it is.
    for v in bm.verts:
        v.co.x *= SHIP_SX
        v.co.y = G.y(0) + (v.co.y - G.y(0)) * SHIP_SY
    return to_object("assembly-newsh9-92", bm, mats, coll)


# --- cutting, normals, shells --------------------------------------------------------------------

def keep_normals(piece, whole, offset, fill_mat=None):
    """Faces split_assembly filled along the cuts go flat (and dark, fill_mat); every smooth corner
    takes the uncut object's normal, so the shading runs on across the cuts."""
    from mathutils.bvhtree import BVHTree
    from mathutils.interpolate import poly_3d_calc
    mesh = piece.data
    hw, hh, eps = 1.0, 14 / 12, 1e-4
    for poly in mesh.polygons:
        vs = [mesh.vertices[i].co for i in poly.vertices]
        if any(all(abs(v.x - b) < eps for v in vs) for b in (-hw, hw)) or \
                any(all(abs(v.y - b) < eps for v in vs) for b in (-hh, hh)):
            poly.use_smooth = False
            if fill_mat is not None:
                poly.material_index = fill_mat
    src = whole.data
    smooth = [p.index for p in src.polygons if p.use_smooth]
    tree = BVHTree.FromPolygons([v.co.copy() for v in src.vertices], [list(src.polygons[i].vertices) for i in smooth])
    corner = src.corner_normals
    off = Vector((offset[0], offset[1], 0.0))
    normals = []
    for poly in mesh.polygons:
        for li in poly.loop_indices:
            if not poly.use_smooth:
                normals.append(poly.normal.copy())
                continue
            co = mesh.vertices[mesh.loops[li].vertex_index].co + off
            hit, _, fi, _ = tree.find_nearest(co)
            sp = src.polygons[smooth[fi]]
            w = poly_3d_calc([src.vertices[v].co for v in sp.vertices], hit)
            nrm = Vector()
            for wk, lk in zip(w, sp.loop_indices):
                nrm += wk * corner[lk].vector
            normals.append(nrm.normalized() if nrm.length > 1e-6 else poly.normal.copy())
    mesh.normals_split_custom_set(normals)


def split_open(obj, layout, coll, shell=True, trim=None):
    """Cut a mesh into the pieces' boxes with no fill: the outline shell (an outline is a skin,
    D90/D118) and, with shell=False, the sphere's own pieces (they always draw together, so a
    filled cut only adds faces, and its n-gon fills of the lens's profile showed in game)."""
    out = {}
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)
        for co, no in (((x0 - 1, 0, 0), (-1, 0, 0)), ((x0 + 1, 0, 0), (1, 0, 0)),
                       ((0, y0 - 14 / 12, 0), (0, -1, 0)), ((0, y0 + 14 / 12 - (trim or {}).get(name, 0) / 12, 0), (0, 1, 0))):
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co,
                                   plane_no=no, clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        nm = f"{name}_outline" if shell else name
        me = bpy.data.meshes.new(nm)
        bm.to_mesh(me)
        bm.free()
        for mm in obj.data.materials:
            me.materials.append(mm)
        s = bpy.data.objects.new(nm, me)
        coll.objects.link(s)
        if shell:
            s.data.shade_smooth()
            s["tyrian_outline"] = True
        out[name] = s
    return out


OVERLAP_SINK = 0.04


def sink_overlap(piece, cy):
    """Sink a lower piece's copy of rows 42-55 (sphere px) under the top pieces' surface."""
    me = piece.data
    for vt in me.vertices:
        v = 35 - (vt.co.y - cy / 12) / PX     # sphere row of the vertex (local y + piece offset)
        if v < 56.0:
            vt.co.z -= OVERLAP_SINK * smoothstep((56.0 - v) / 1.0)
    me.update()


def shell_for(whole, coll, faces):
    sealed = whole.copy()
    sealed.data = whole.data.copy()
    coll.objects.link(sealed)
    bpy.context.view_layer.update()
    shell = common.outline_shell(sealed, coll, voxel=0.012, faces=faces, smooth=4, inside=0.003, islands="outer")
    bpy.data.objects.remove(sealed)
    bpy.context.view_layer.update()
    return shell


def tris(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)


def main(only=None):
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else OUT
    pieces_dir = Path(argv[argv.index("--pieces") + 1]) if "--pieces" in argv else None
    bpy.ops.wm.read_factory_settings(use_empty=True)
    coll = common.reset_collection(NAME)
    info = {}
    groups = {}

    # the eye sphere
    grid = sphere_grid()
    fit_rim(grid)
    sprite = merged_sprite(TOP + LOW)
    sphere, slots = build_sphere(sprite, coll)
    shell = shell_for(sphere, coll, faces=14000)
    # The lower assembly's top 14 rows repeat the top one's rows 42-55 pixel for pixel, and both
    # always draw together (one rigid link, spawned on one tick, armour 255): the lower pieces
    # (body and shell) start at row 56. Two coincident copies of that band drew a dark sliver and
    # ink lines across the lens in game (a depth/shadow fight; sinking the copy 0.04-0.08 under
    # the top's did not clear it). --overlap keeps the lower pieces' full boxes, sunk.
    trim = None if "--overlap" in argv else {n: 14 for n in LOW}
    pieces = split_open(sphere, SPH_LAYOUT, coll, shell=False, trim=trim)
    # the lower pieces' shells always stop at row 56: two open shells over one band drew ink lines
    shells = split_open(shell, SPH_LAYOUT, coll, trim={n: 14 for n in LOW})
    bpy.data.objects.remove(shell)
    if trim is None:
        for name, cx, cy in SPH_LAYOUT:
            if name in LOW:
                sink_overlap(pieces[name], cy)
    for name, cx, cy in SPH_LAYOUT:
        keep_normals(pieces[name], sphere, (cx / 12, -cy / 12), slots["fill"])
        for o in (pieces[name], shells[name]):
            o.location = (cx / 12, -cy / 12, 0)
        groups[name] = [pieces[name], shells[name]]
    # One shared anchor for all nine pieces (D181/D185): the ball's mid height goes on the camera
    # ray, so its eye and cowl land where the sprite has them and its top is not lost past the
    # far edge when it enters from the top of the screen (LAVA RUN).
    for name, _, _ in SPH_LAYOUT:
        for o in groups[name]:
            o["tyrian_anchor"] = SPHERE_ANCHOR
    info["sphere_whole_tris"] = tris(sphere)
    sphere["whole"] = "sphere"

    # the shield ship
    ssprite = merged_sprite(SHIP)
    ship = build_ship(ssprite, coll)
    sshell = shell_for(ship, coll, faces=6000)
    lay = [(e["model"], e["cx"] - SHIP_CENTRE[0], e["cy"] - SHIP_CENTRE[1]) for e in ssprite["assemblyLayout"]
           if e["model"] in SHIP]
    sp = common.split_assembly(ship, lay)
    ssh = split_open(sshell, lay, coll)
    bpy.data.objects.remove(sshell)
    for name, cx, cy in lay:
        keep_normals(sp[name], ship, (cx / 12, -cy / 12))
        for o in (sp[name], ssh[name]):
            o.location = (cx / 12 + SHIP_DX, -cy / 12, 0)
        groups[name] = [sp[name], ssh[name]]
    info["ship_whole_tris"] = tris(ship)
    ship["whole"] = "ship"
    ship.location = (SHIP_DX, 0, 0)

    bad = [g[1].name for g in groups.values() if len(g[1].data.polygons) == 0]
    if bad:
        raise SystemExit(f"empty outline shells: {bad}")
    info["pieces"] = {n: {"tris": tris(g[0]), "outline_tris": tris(g[1])} for n, g in groups.items()}
    bpy.context.view_layer.update()
    mine = list(only) if only else list(groups)
    for name in mine:
        group = groups[name]
        saved = [tuple(o.location) for o in group]
        for o in group:
            o.location = (0, 0, 0)
        bpy.context.view_layer.update()
        common.export_sprite_model(ROOT, group, f"enemies/{name}", load(name)["sprites"])
        for o, loc in zip(group, saved):
            o.location = loc
        bpy.context.view_layer.update()
    if "--out" in argv:
        common.export_glb([o for g in groups.values() for o in g], out)
    if pieces_dir:
        pieces_dir.mkdir(parents=True, exist_ok=True)
        common.export_glb([sphere, ship], pieces_dir / "wholes.glb")
        for name, group in groups.items():
            saved = [tuple(o.location) for o in group]
            for o in group:
                o.location = (0, 0, 0)
            bpy.context.view_layer.update()
            common.export_glb(group, pieces_dir / f"{name}.glb")
            for o, loc in zip(group, saved):
                o.location = loc
            bpy.context.view_layer.update()
        (pieces_dir / "build_info.json").write_text(json.dumps(info, indent=1))
    print("BUILD_INFO", json.dumps(info))

