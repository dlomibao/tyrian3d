"""Armoured EYE SPHERE (newsh9.shp: assembly-newsh9-191 + assembly-newsh9-210): shared builder.

Episode 4 QA rework (D65 hard-surface standard). LAVA RUN (4.4) and EYESPY (4.20) fly one machine
drawn by two rigid assemblies on one link: the top 72x56 px (newsh9 153/155/157 over 191/193/195)
and the lower 72x28 px (210/212/214), whose first 14 rows repeat the top's rows 42-55. Built once,
whole, in sphere coordinates (px u right, v down, 72 x 70; +Y north = sprite up) and cut into the
nine pieces. EYESPY shows its screen flipped, so there the eye is at the top and the swirl below it.
The grey shield ship that once shared this builder stays in lib_b019.py (assembly-newsh9-92).

Cross-sections (sprite px; 1 unit = 12 px):
  - BALL: faired ellipsoid on the inner-mask rim (per-degree fit, 16 Fourier terms), crown 24 px,
    plain closed underside 20 px; armour plates parted by modelled seam grooves (the accepted armour,
    as lib_b019 built it).
  - SWIRL (yin-yang armour boss, upper left): two interlocking crowned plates on one elliptical
    plan, the light head lobe A (pal 11) and lobe B (pal 9), each rolling over a fillet onto the
    ball; the S-shaped parting line between them is a real groove (exact boolean, dark pal 2) that
    runs out through the rim at both ends; a rounded tail rib (pal 10) runs from the light bar's
    foot down and left under the boss towards the lens rim, as the sprite's light arc (rows 26-37).
  - LIGHT BAR: glowing crescent (pal 132, metallic 1 / rough, D126/D173) in a dark recessed bezel.
  - EYE: a socket plane fitted (least squares) through the ball round the lens ellipse (centre
    (35.5, 50.5), 20.5 x 14.5 px); the lens is one smooth convex dome on it, crown 1.8 px proud of
    the ball, in the sprite's colours as flush material regions laid along the lens's own rings and
    spokes (crisp, no per-pixel stair-steps): azure iris 157 with light-cyan 139 / bright 159
    patches upper left (the sprite's streaks: colour, not geometry, art rule 2), a teal crescent
    130 round the lower right with darker 54 patches and darker 130 patches in the right panes, a
    dark-blue limbal ring 54; a slightly domed glossy black pupil cap (pal 1) at the sprite's place;
    the CROSS as two full-length raised mullions (pal 97, rounded tops), vertical at col 36,
    horizontal at row 51 left / row 50 right; a machined bezel ring (pal 3).
Underside: plain closed cap (art rule 3).

Outline shell (D51): from a sealed copy of the whole, islands="outer" (D189), cut open per piece;
every _outline node is checked non-empty.

Wrappers: assembly-newsh9-191.py (the six top pieces) and assembly-newsh9-210.py (the three lower
pieces) call main(only=[...]) and export only their own models (public/models/enemies/<piece>.glb +
src/render/spriteModels/<piece>.json). Optional flags after "--": --out X.glb writes the combined
review glb, --pieces DIR one glb per piece and build_info.json. A normal build writes nothing else.
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
PX = 1 / 12

TOP = ["newsh9-153", "newsh9-155", "newsh9-157", "newsh9-191", "newsh9-193", "newsh9-195"]
LOW = ["newsh9-210", "newsh9-212", "newsh9-214"]
SW, SH = 72, 70
LOW_ROW = 42
SPH_LAYOUT = ([(n, -24 + 24 * (i % 3), -21 + 28 * (i // 3)) for i, n in enumerate(TOP)]
              + [(n, -24 + 24 * i, LOW_ROW + 14 - 35) for i, n in enumerate(LOW)])


def load(name):
    return common.load_sprite(ROOT, name)


def merged_sprite(names):
    data = load(names[0])
    for n in names[1:]:
        data["colors"].update(load(n)["colors"])
    return data


def sphere_grid():
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

OU, OV = 36.0, 35.0
HT, HB = 24 * PX, 20 * PX
SPHERE_ANCHOR = 12 * PX


def X(u):
    return (u - SW / 2) * PX


def Y(v):
    return (SH / 2 - v) * PX


RIM = []
RIM_N = 360
RIM_HARM, RIM_PAD = 16, 0.12


def fit_rim(grid):
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
    coef = []
    for h in range(RIM_HARM + 1):
        a = sum(raw[k] * math.cos(2 * math.pi * h * k / RIM_N) for k in range(RIM_N)) * 2 / RIM_N
        b = sum(raw[k] * math.sin(2 * math.pi * h * k / RIM_N) for k in range(RIM_N)) * 2 / RIM_N
        coef.append((a / 2 if h == 0 else a, b))
    RIM[:] = [sum(a * math.cos(2 * math.pi * h * k / RIM_N) + b * math.sin(2 * math.pi * h * k / RIM_N)
                  for h, (a, b) in enumerate(coef)) + RIM_PAD for k in range(RIM_N)]
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
    p = min(1.0, rho(u, v))
    return HT * math.sqrt(max(0.0, 1 - p * p))


def normal_of(surface, u, v):
    d = 0.3
    dzdu = (surface(u + d, v) - surface(u - d, v)) / (2 * d)
    dzdv = (surface(u, v + d) - surface(u, v - d)) / (2 * d)
    return Vector((-dzdu / PX, dzdv / PX, 1.0)).normalized()


def smoothstep(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


# --- mesh helpers (copied from lib_b019; shared files stay untouched) ---------------------------

def resample(path, step):
    out = [path[0]]
    for a, b in zip(path, path[1:]):
        n = max(1, int(math.ceil(math.hypot(b[0] - a[0], b[1] - a[1]) / step)))
        for i in range(1, n + 1):
            t = i / n
            out.append(tuple(x + (y - x) * t for x, y in zip(a, b)))
    return out


def catmull(ctrl, n=6):
    out = []
    for i in range(len(ctrl) - 1):
        p0, p1, p2, p3 = ctrl[max(0, i - 1)], ctrl[i], ctrl[i + 1], ctrl[min(len(ctrl) - 1, i + 2)]
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * (2 * p1[j] + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in range(len(p1))))
    out.append(tuple(ctrl[-1]))
    return out


def sweep(bm, path, sides=8, mat=0, smooth=True, surface=zb, step=1.5, power=1.0):
    """A tube lying on a surface along (u, v, lift, half_width_px, half_height) points."""
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
    for f in set(bm.faces) - before:
        f.material_index = mat
        f.smooth = smooth


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


def to_object(name, bm, mats, coll, recalc=True):
    if recalc:
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    return obj


def _bm_to_mesh(b):
    me = bpy.data.meshes.new("tmp")
    b.to_mesh(me)
    b.free()
    return me


def cut_grooves(name, part, grooves, mats, coll):
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


# --- the swirl: yin-yang armour boss -------------------------------------------------------------

# The plan: an ellipse whose long axis (SRY, the classic yin-yang's seam axis) runs from the
# west-south-west, under the head, to the east-north-east at the light bar's foot, 20 deg above the
# horizontal; the S parting line joins its two ends through the centre, as the sprite's dark seam
# does: (17,26) under the head, up between the two heads (col 29-30), then east along row 17-18.
SC_U, SC_V, SRX, SRY = 28.5, 21.8, 11.0, 12.5
PHI = math.radians(20.0)
AX_Q = (math.cos(PHI), math.sin(PHI))                      # seam axis, toward the ENE end (north-up)
AX_P = (math.cos(PHI - math.pi / 2), math.sin(PHI - math.pi / 2))   # across it, toward the SSE
H_A, H_B = 1.5 * PX, 0.9 * PX       # lobe heights over the ball
FILLET = 0.2                       # edge roll, as a share of the plan radius


def sw_uv(p, q):
    """Local unit-disc coords (p across the seam axis toward SSE, q along it toward ENE) -> (u, v)."""
    x = p * SRX * AX_P[0] + q * SRY * AX_Q[0]
    y = p * SRX * AX_P[1] + q * SRY * AX_Q[1]
    return SC_U + x, SC_V - y


def sw_pq(u, v):
    x, y = u - SC_U, SC_V - v
    return (x * AX_P[0] + y * AX_P[1]) / SRX, (x * AX_Q[0] + y * AX_Q[1]) / SRY


def lobe_of(p, q):
    """1 = lobe A (the light head, north-west, its tail over the top to the ENE end), 0 = lobe B
    (head south-east by the bar's foot, its tail under A to the WSW end)."""
    if math.hypot(p, q + 0.5) < 0.5:
        return 1
    if math.hypot(p, q - 0.5) < 0.5:
        return 0
    return 1 if p < 0 else 0


def seam_dist(p, q):
    """Distance (unit disc) to the S parting line."""
    d = 9.0
    if p <= 0.02 and q >= -0.02:
        d = min(d, abs(math.hypot(p, q - 0.5) - 0.5))
    if p >= -0.02 and q <= 0.02:
        d = min(d, abs(math.hypot(p, q + 0.5) - 0.5))
    return d


def pad_profile(r):
    if r <= 1 - FILLET:
        return 1.0 - 0.05 * (r / (1 - FILLET)) ** 2
    t = (r - (1 - FILLET)) / FILLET
    return 0.95 * math.sqrt(max(0.0, 1 - t * t))


def zpad(u, v):
    p, q = sw_pq(u, v)
    r = math.hypot(p, q)
    if r >= 1.0:
        return zb(u, v)
    # the lobes' heights blend inside the groove only
    s = seam_dist(p, q)
    a = lobe_of(p, q)
    h_here, h_other = (H_A, H_B) if a else (H_B, H_A)
    h = h_here if s > 0.05 else h_other + (h_here - h_other) * (0.5 + 0.5 * s / 0.05)
    return zb(u, v) + h * pad_profile(r)


def s_path():
    """The S parting line, ENE end -> centre -> WSW end (sprite px), run out past the rim."""
    pts = [(0.0, 1.14)]
    for i in range(0, 25):
        t = math.pi / 2 - math.pi * i / 24                 # upper circle, its p < 0 side
        pts.append((-0.5 * math.cos(t), 0.5 + 0.5 * math.sin(t)))
    for i in range(1, 25):
        t = math.pi / 2 - math.pi * i / 24                 # lower circle, its p > 0 side
        pts.append((0.5 * math.cos(t), -0.5 + 0.5 * math.sin(t)))
    pts.append((0.0, -1.14))
    return [sw_uv(p, q) for p, q in pts]


# --- the eye ----------------------------------------------------------------------------------------

LCU, LCV, LA, LB = 35.5, 50.5, 20.5, 14.5
PL = [0.0, 0.0, 0.0]
LENS_PROUD = 1.8 * PX
BULGE = [0.0]


def fit_lens_plane():
    import numpy as np
    rows, zs = [], []
    for k in range(96):
        g = 2 * math.pi * k / 96
        u, v = LCU + 1.06 * LA * math.cos(g), LCV + 1.06 * LB * math.sin(g)
        rows.append([1.0, u, v])
        zs.append(zb(u, v))
    sol = np.linalg.lstsq(np.array(rows), np.array(zs), rcond=None)[0]
    PL[:] = [float(x) for x in sol]
    BULGE[0] = zb(LCU, LCV) - plane(LCU, LCV) + LENS_PROUD


def plane(u, v):
    return PL[0] + PL[1] * u + PL[2] * v


def e_of(u, v):
    return math.hypot((u - LCU) / LA, (v - LCV) / LB)


def zl(u, v):
    e = min(1.0, e_of(u, v))
    return plane(u, v) + 0.3 * PX + BULGE[0] * (1 - e * e) ** 0.55


def lens_uv(e, g):
    """g measured in the sprite's frame: 0 = east, pi/2 = south (v grows down)."""
    return LCU + LA * e * math.cos(g), LCV + LB * e * math.sin(g)


E_LIMB = 0.9


def crescent_in(g):
    """Inner edge (e) of the teal crescent; E_LIMB where there is none. g: 0 east, pi/2 south.
    The band runs from the upper right (-75 deg) round the east and the south to 200 deg, widest
    at about 40 deg (lower right), as the sprite's teal 129-131 / dark blue 54-56 sit; the upper
    left stays azure."""
    d = math.degrees(g) % 360
    if d > 270:
        d -= 360
    if d < -75 or d > 200:
        return E_LIMB
    s = (d + 75) / 275
    w = 0.42 * math.sin(math.pi * s) ** 1.1 * (0.6 + 0.4 * math.cos(math.radians(d - 40) * 0.6))
    return E_LIMB - max(0.0, w)


# --- build ---------------------------------------------------------------------------------------

def build_sphere(sprite, coll):
    tag = "nsh9a"
    mats, slots = [], {}

    def M(key, i, **kw):
        if key not in slots:
            slots[key] = len(mats)
            mats.append(common.palette_material(sprite, i, f"{tag}{key}", **kw))
        return slots[key]

    BALL = M("ball", 6, metallic=0.4, roughness=0.45)
    SEAM = M("seam", 2, metallic=0.3, roughness=0.65)
    LOBEA = M("lobea", 11, metallic=0.55, roughness=0.42)
    LOBEB = M("lobeb", 9, metallic=0.55, roughness=0.45)
    SGROOVE = M("sgroove", 2, metallic=0.3, roughness=0.7)
    TAIL = M("tail", 10, metallic=0.7, roughness=0.32)
    BEZEL = M("bezel", 3, metallic=0.45, roughness=0.55)
    STRIP = M("strip", 132, metallic=1.0, roughness=0.55, emission_strength=0.8)
    ROD = M("rod", 12, metallic=0.85, roughness=0.28)
    SLOT = M("slot", 2, metallic=0.3, roughness=0.7)
    RING = M("ring", 6, metallic=0.6, roughness=0.36)
    LID = M("lid", 5, metallic=0.55, roughness=0.4)
    # glow surfaces: metallic 1 / rough (D126/D173), so they read as their colour, not a reflection
    IRIS = M("iris", 157, metallic=1.0, roughness=0.5, emission_strength=0.22)
    TEAL = M("teal", 130, metallic=1.0, roughness=0.5, emission_strength=0.35)
    LIMB = M("limb", 54, metallic=1.0, roughness=0.55, emission_strength=0.2)
    CYAN = M("cyan", 139, metallic=1.0, roughness=0.5, emission_strength=0.3)
    BRIGHT = M("bright", 159, metallic=1.0, roughness=0.5, emission_strength=0.25)
    CROSS = M("cross", 97, metallic=0.3, roughness=0.4)
    # black glass: a dielectric with a low F0 (Specular IOR Level, D176), so the domed cap catches
    # the game light as a soft sheen and stays black (glossier read grey or as a cartoon glint)
    PUPIL = M("pupil", 1, metallic=0.0, roughness=0.45)
    pb = next(n for n in mats[PUPIL].node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    if "Specular IOR Level" in pb.inputs:
        pb.inputs["Specular IOR Level"].default_value = 0.2
    FILL = M("fill", 2, metallic=0.3, roughness=0.7)

    # ---- the ball (unchanged armour) ----
    segs, nr = 96, 18
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
            f.material_index, f.smooth = BALL, True

    def groove(points, surface=zb, w=0.75, h=0.1, mat=SEAM, step=0.8):
        # a closed cutter (pointed ends): an open tube is not a solid and the exact boolean then
        # left the groove walls inverted / invisible (lib_b019's seams only showed as ink)
        t = bmesh.new()
        (ua, va), (ub, vb) = points[0], points[1]
        (uy, vy), (uz, vz) = points[-2], points[-1]
        la = math.hypot(ub - ua, vb - va) or 1.0
        lz = math.hypot(uz - uy, vz - vy) or 1.0
        start = (ua - (ub - ua) / la * 1.2, va - (vb - va) / la * 1.2, 0.0, 0.0, 0.0)
        end = (uz + (uz - uy) / lz * 1.2, vz + (vz - vy) / lz * 1.2, 0.0, 0.0, 0.0)
        sweep(t, [start] + [(u, v, 0.0, w, h) for u, v in points] + [end], sides=6, mat=mat, surface=surface,
              step=step, smooth=False)
        return t

    seams = [
        [(23.6, 2.6), (25.4, 6.0), (27.0, 8.6)],
        [(37.2, 1.4), (35.8, 5.0), (34.6, 8.8)],
        [(41.0, 2.8), (44.0, 6.4), (48.0, 9.6), (50.0, 13.0)],
        [(49.6, 13.4), (54.0, 13.6), (59.0, 13.4), (65.5, 13.6)],
        [(49.6, 13.4), (49.4, 20.0), (49.4, 27.0), (49.8, 35.0)],
        [(50.4, 26.0), (54.0, 25.8), (58.0, 26.4), (63.6, 27.4)],
        [(50.0, 35.2), (54.0, 35.6), (57.4, 36.6)],
        [(1.6, 20.6), (5.0, 22.2), (9.0, 23.6), (15.6, 24.6)],
        [(1.2, 36.0), (4.0, 37.0)],
        [(15.0, 30.2), (20.0, 31.2), (24.0, 31.6)],
        [(12.0, 43.6), (14.0, 40.0), (16.2, 36.8), (21.0, 35.4)],
        [(51.0, 37.4), (54.4, 40.0), (56.2, 43.0)],
    ]
    bm = bmesh.new()
    bm.from_mesh(cut_grooves(NAME + "_ball", bb, [groove(p) for p in seams], mats, coll))

    # ---- the swirl boss: one crowned elliptical plate, split into two lobes by an S groove ----
    bp = bmesh.new()
    NA, rr = 84, [0.0, 0.08, 0.16, 0.25, 0.34, 0.43, 0.52, 0.6, 0.67, 0.73, 0.78, 0.83, 0.87, 0.905,
                   0.935, 0.96, 0.98, 0.993, 1.0]
    prings = []
    for r in rr:
        if r == 0:
            u, v = sw_uv(0, 0)
            prings.append([bp.verts.new((X(u), Y(v), zpad(u, v)))])
            continue
        ring_ = []
        for k in range(NA):
            g = 2 * math.pi * k / NA
            u, v = sw_uv(r * math.cos(g), r * math.sin(g))
            z = zpad(u, v) if r < 1 else zb(u, v) - 0.03
            ring_.append(bp.verts.new((X(u), Y(v), z)))
        prings.append(ring_)
    u0, v0 = sw_uv(0, 0)
    pfloor = [bp.verts.new((X(u0), Y(v0), zb(u0, v0) - 0.1))]
    for r0, r1 in zip(prings, prings[1:]):
        for f in bridge(bp, r0, r1):
            f.smooth = True
    for f in bridge(bp, prings[-1], pfloor):
        f.smooth = False
        f.material_index = FILL
    bp.faces.ensure_lookup_table()
    for f in bp.faces:
        if f.material_index == FILL:
            continue
        c = f.calc_center_median()
        u = c.x / PX + SW / 2
        v = SH / 2 - c.y / PX
        p, q = sw_pq(u, v)
        f.material_index = LOBEA if lobe_of(p, q) else LOBEB
    spath = s_path()
    stube = groove(spath, surface=zpad, w=1.05, h=0.1, mat=SGROOVE, step=0.6)
    bm.from_mesh(cut_grooves(NAME + "_swirl", bp, [stube], mats, coll))

    # the tail rib: the sprite's light arc, from the lens rim (upper left) under the boss and up
    # into the light bar's foot; thin at the rim, full under the boss
    tail_c = [(22.6, 36.2), (24.4, 35.3), (26.8, 34.3), (29.8, 33.2), (33.2, 32.1), (36.8, 30.8),
              (40.0, 29.0), (42.4, 26.8), (43.8, 25.0)]
    tl = catmull(tail_c, 4)
    n = len(tl)
    tail = [(tl[0][0] - 0.75, tl[0][1] + 0.38, 0.0, 0.0, 0.0)]
    for i, (u, v) in enumerate(tl):
        t = i / (n - 1)
        full = smoothstep(t / 0.4) - 0.3 * smoothstep((t - 0.65) / 0.35)
        tail.append((u, v, 0.0, 0.85 + 0.7 * full, 0.055 + 0.035 * full))
    tail.append((tl[-1][0] + 0.3, tl[-1][1] - 0.9, 0.0, 0.0, 0.0))
    sweep(bm, tail, sides=12, mat=TAIL, power=0.6, step=1.0)

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
        for u, v in (path[0], path[2]):
            sweep(bm, [(u - 0.9, v, 0.02, 1.3, 0.11), (u + 0.9, v, 0.02, 1.3, 0.11)], sides=8, mat=RING,
                  power=0.5, step=2.0)

    # ---- the eye: a convex lens in a socket ----
    fit_lens_plane()
    be = bmesh.new()
    NE = 72

    def vert(u, v, z):
        return be.verts.new((X(u), Y(v), z))

    # ring parameters t -> e(t, g): iris rings up to the crescent's inner edge, crescent rings up to
    # the limbus, limbal rings up to the rim (so every colour change runs along a ring)
    iris_t = [0.1, 0.2, 0.32, 0.45, 0.58, 0.7, 0.8, 0.9, 1.0]
    cres_t = [0.5, 1.0]
    limb_e = [0.95, 0.985, 1.0]
    centre = [vert(LCU, LCV, zl(LCU, LCV))]
    rings_e = [centre]
    kinds = []
    for t in iris_t:
        rg = []
        for k in range(NE):
            g = 2 * math.pi * k / NE
            e = crescent_in(g) * t
            u, v = lens_uv(e, g)
            rg.append(vert(u, v, zl(u, v)))
        rings_e.append(rg)
        kinds.append(IRIS)
    for t in cres_t:
        rg = []
        for k in range(NE):
            g = 2 * math.pi * k / NE
            ci = crescent_in(g)
            e = ci + (E_LIMB - ci) * t
            u, v = lens_uv(e, g)
            rg.append(vert(u, v, zl(u, v)))
        rings_e.append(rg)
        kinds.append("cres")
    for e in limb_e:
        rg = []
        for k in range(NE):
            g = 2 * math.pi * k / NE
            u, v = lens_uv(e, g)
            rg.append(vert(u, v, zl(u, v)))
        rings_e.append(rg)
        kinds.append(LIMB)
    for (r0, r1), kind in zip(zip(rings_e, rings_e[1:]), kinds):
        for k, f in enumerate(bridge(be, r0, r1)):
            f.smooth = True
            if kind == "cres":
                g = 2 * math.pi * (k + 0.5) / NE
                f.material_index = TEAL if crescent_in(g) < E_LIMB - 0.02 else IRIS
            else:
                f.material_index = kind
    # the rim wall down into the socket, and a floor (closed solid)
    wall = [vert(*lens_uv(1.0, 2 * math.pi * k / NE), 0) for k in range(NE)]
    for k, w in enumerate(wall):
        u, v = lens_uv(1.0, 2 * math.pi * k / NE)
        w.co.z = min(zb(u, v), plane(u, v)) - 0.1
    for f in bridge(be, rings_e[-1], wall):
        f.material_index, f.smooth = BEZEL, False
    flo = [vert(LCU, LCV, plane(LCU, LCV) - 0.12)]
    for f in bridge(be, wall, flo):
        f.material_index, f.smooth = FILL, False
    bm.from_mesh(_bm_to_mesh(be))

    # the iris tone patches (B's tones on A's lens): flush colour, not geometry (art rule 2). Each
    # is a soft, slightly irregular blob laid in the lens's own (angle, ring) coordinates, so it
    # bends with the rings, and its edge is a smooth curve (no per-face or per-pixel steps); placed
    # where the sprite has its tones. It lies PATCH_LIFT on the lens, a skin, not a relief.
    # (centre angle deg: 0 east, 90 south; centre e (0 centre, 1 rim); half width deg; half
    # height in e; shape phase; colour)
    PATCH_LIFT = 0.12 * PX
    patches = [
        # light cyan / bright azure upper left (the sprite's 137-143 streaks and its 62 glint)
        (228, 0.63, 17, 0.15, 0.3, CYAN), (264, 0.6, 9, 0.17, 1.2, CYAN),
        (244, 0.4, 7, 0.08, 0.7, BRIGHT), (194, 0.62, 9, 0.1, 1.6, BRIGHT),
        # darker steel-teal / deep blue in the right and lower right panes
        (302, 0.6, 14, 0.16, 0.4, TEAL), (34, 0.44, 17, 0.09, 1.0, LIMB),
        (88, 0.6, 22, 0.07, 2.2, LIMB), (20, 0.82, 12, 0.05, 0.9, IRIS),
    ]
    bpt = bmesh.new()
    NPB = 18
    for gc, ec, hw, he, ph, mat in patches:
        def at(sc, th):
            f = 1 + 0.16 * math.cos(2 * th + ph) + 0.09 * math.cos(3 * th + 2 * ph)
            g = math.radians(gc + hw * sc * f * math.cos(th))
            u, v = lens_uv(ec + he * sc * f * math.sin(th), g)
            return bpt.verts.new(Vector((X(u), Y(v), zl(u, v))) + normal_of(zl, u, v) * PATCH_LIFT)
        c0 = [at(0.0, 0.0)]
        r1 = [at(0.55, 2 * math.pi * k / NPB) for k in range(NPB)]
        r2 = [at(1.0, 2 * math.pi * k / NPB) for k in range(NPB)]
        fs = [bpt.faces.new((c0[0], r1[k], r1[(k + 1) % NPB])) for k in range(NPB)]
        fs += [bpt.faces.new((r1[k], r2[k], r2[(k + 1) % NPB], r1[(k + 1) % NPB])) for k in range(NPB)]
        for f in fs:
            f.material_index, f.smooth = mat, True
    # face them all up (outward); they join the whole after its normals are recalculated (an open
    # skin has no inside for the recalc to find)
    bpt.normal_update()
    for f in bpt.faces:
        if f.normal.z < 0:
            f.normal_flip()
    patch_mesh = _bm_to_mesh(bpt)

    # the pupil: a solid black cap, lens-shaped, its edge tucked into the lens
    PU, PV, PRU, PRV = 33.6, 51.8, 4.9, 5.4
    bpup = bmesh.new()
    prs = []
    for s, lift in ((0.0, 0.42 * PX), (0.35, 0.38 * PX), (0.65, 0.29 * PX), (0.85, 0.18 * PX),
                    (0.96, 0.07 * PX), (1.0, -0.15 * PX)):
        if s == 0:
            prs.append([bpup.verts.new((X(PU), Y(PV), zl(PU, PV) + lift))])
            continue
        rg = []
        for k in range(40):
            g = 2 * math.pi * k / 40
            u, v = PU + PRU * s * math.cos(g), PV + PRV * s * math.sin(g)
            rg.append(bpup.verts.new((X(u), Y(v), zl(u, v) + lift)))
        prs.append(rg)
    pbot = [bpup.verts.new((X(PU), Y(PV), zl(PU, PV) - 0.3 * PX))]
    for r0, r1 in zip(prs, prs[1:]):
        for f in bridge(bpup, r0, r1):
            f.material_index, f.smooth = PUPIL, True
    for f in bridge(bpup, prs[-1], pbot):
        f.material_index, f.smooth = PUPIL, False
    bm.from_mesh(_bm_to_mesh(bpup))

    # the cross: two full-length raised mullions following the dome (vertical col 36; horizontal
    # row 51 west of the pupil, row 50 east of it)
    def mullion(ctrl):
        line = catmull(ctrl, 6)
        line = [p for p in line if e_of(*p) <= 0.975]
        pts = [(line[0][0], line[0][1], 0.0, 0.0, 0.0)]
        for i, (u, v) in enumerate(line):
            pts.append((u, v, 0.08 * PX, 0.62, 0.42 * PX))
        pts.append((line[-1][0], line[-1][1], 0.0, 0.0, 0.0))
        # the ends: shorten the taper so the bar meets the limbus square
        pts[0] = (line[0][0], line[0][1], 0.0, 0.45, 0.25 * PX)
        pts[-1] = (line[-1][0], line[-1][1], 0.0, 0.45, 0.25 * PX)
        sweep(bm, pts, sides=6, mat=CROSS, surface=zl, step=1.0, power=0.55)

    mullion([(36.5, LCV - LB), (36.5, 43.0), (36.5, 50.5), (36.5, 58.0), (36.5, LCV + LB)])
    mullion([(LCU - LA, 51.6), (22.0, 51.5), (30.0, 51.3), (36.5, 50.9), (44.0, 50.5), (LCU + LA, 50.4)])

    # the bezel: a machined ring round the lens
    NB = 120
    ring_pts = []
    for k in range(NB + 1):
        g = 2 * math.pi * k / NB
        u, v = LCU + (LA + 1.0) * math.cos(g), LCV + (LB + 1.0) * math.sin(g)
        ring_pts.append((u, v, 0.02, 1.15, 0.07))
    sweep(bm, ring_pts[:NB // 2 + 1], sides=8, mat=BEZEL, step=1.8, power=0.7)
    sweep(bm, ring_pts[NB // 2:], sides=8, mat=BEZEL, step=1.8, power=0.7)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.from_mesh(patch_mesh)
    bpy.data.meshes.remove(patch_mesh)
    obj = to_object(NAME, bm, mats, coll, recalc=False)
    return obj, slots


# --- cutting, normals, shells (copied from lib_b019) ----------------------------------------------

def keep_normals(piece, whole, offset, fill_mat=None):
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
    out = {}
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)
        for co, no in (((x0 - 1, 0, 0), (-1, 0, 0)), ((x0 + 1, 0, 0), (1, 0, 0)),
                       ((0, y0 - 14 / 12, 0), (0, -1, 0)),
                       ((0, y0 + 14 / 12 - (trim or {}).get(name, 0) / 12, 0), (0, 1, 0))):
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
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else None
    pieces_dir = Path(argv[argv.index("--pieces") + 1]) if "--pieces" in argv else None
    bpy.ops.wm.read_factory_settings(use_empty=True)
    coll = common.reset_collection(NAME)
    info = {}
    groups = {}
    grid = sphere_grid()
    fit_rim(grid)
    sprite = merged_sprite(TOP + LOW)
    sphere, slots = build_sphere(sprite, coll)
    shell = shell_for(sphere, coll, faces=14000)
    trim = {n: 14 for n in LOW}
    pieces = split_open(sphere, SPH_LAYOUT, coll, shell=False, trim=trim)
    shells = split_open(shell, SPH_LAYOUT, coll, trim=trim)
    bpy.data.objects.remove(shell)
    for name, cx, cy in SPH_LAYOUT:
        keep_normals(pieces[name], sphere, (cx / 12, -cy / 12), slots["fill"])
        for o in (pieces[name], shells[name]):
            o.location = (cx / 12, -cy / 12, 0)
            o["tyrian_anchor"] = SPHERE_ANCHOR
        groups[name] = [pieces[name], shells[name]]
    bad = [g[1].name for g in groups.values() if len(g[1].data.polygons) == 0]
    if bad:
        raise SystemExit(f"empty outline shells: {bad}")
    info["sphere_whole_tris"] = tris(sphere)
    info["pieces"] = {n: {"tris": tris(g[0]), "outline_tris": tris(g[1])} for n, g in groups.items()}
    info["total_piece_tris"] = sum(v["tris"] for v in info["pieces"].values())
    bpy.context.view_layer.update()
    for name in (list(only) if only else list(groups)):
        group = groups[name]
        saved = [tuple(o.location) for o in group]
        for o in group:
            o.location = (0, 0, 0)
        bpy.context.view_layer.update()
        common.export_sprite_model(ROOT, group, f"enemies/{name}", load(name)["sprites"])
        for o, loc in zip(group, saved):
            o.location = loc
        bpy.context.view_layer.update()
    if out:
        common.export_glb([o for g in groups.values() for o in g], out)
    if pieces_dir:
        pieces_dir.mkdir(parents=True, exist_ok=True)
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

