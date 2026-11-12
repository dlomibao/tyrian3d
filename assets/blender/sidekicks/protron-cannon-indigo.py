"""Protron Cannon Indigo (sidekick option 23, style 2: held 20 px ahead of the ship), final.
tyrian.shp#9 2x2 frame 45, one frame, 24x28 grid (22x15 px drawn), symmetric about column edge 13.

WHAT IT IS (D120/D122): a front-mounted weapon module, not a ship. Read from the sprite:
- core (columns 9-16, rows 10-17, dark navy 48-62, median 53): the emitter housing, a faceted
  lozenge on the axis, pointed fore and aft; its bright 61/62 column is sheen on the lit crown
  facet, not paint. Its flat nose face (row 10) carries the protron muzzle, firing north.
- wings (columns 3-10 / 15-22, rows 7-14, steel blue 128-142, median 134): two swept field vanes
  (accelerator blades) whose diamond tips point forward; the bright diagonal streak is sheen on
  the gable ridge, the blade roots bury into the housing's flanks.
- tails (columns 4-6 / 19-21, rows 15-20, median 132): trailing spars under the vanes' rear edge,
  tapering back to points, each clamped by a dark navy band at row 17 (median 52).

Cross-sections first (the blueprint, blueprint.json): every part is a loft of chamfered sections
between stations along Y, sections pchip-interpolated so nothing swells:
- vane: a flat-bottomed gable plate (outer wall, top chamfer, ridge 1.6 px in from the inner edge,
  inner chamfer, inner wall, bottom chamfers), 2.25 px tall at the ridge, thinning to the tip;
- spar: the same gable, 1.65 px, ridge near its inner edge; the clamp band is a slightly larger
  copy of its section (a sleeve standing 0.14 px proud);
- housing: a ten-sided chamfered lozenge, crown along the axis (pchip through the blueprint's
  crown heights, 3.35 px at its widest), skirt walls 1.15 px, flat nose face.
Machined detail: a lathe-turned muzzle bezel with a stepped bore and a recessed emitter lens
(faintly glowing), root hinge knuckles where the vanes pin into the housing, root bolt heads, two
vent slots on the rear facets, and modelled panel seams (shallow dark grooves) on the vanes and
round the housing's girdle. Underside: flat closed bottoms, no detail.

Texture: AO/roughness bake only (no concept projection), the outline shell (D51).

Run: tools/build-models.sh -j 2 assets/blender/sidekicks/protron-cannon-indigo.py  (or Blender --background --python this [-- --no-bake])
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

NAME = "sidekick-protron-cannon-indigo"
MODEL = "sidekicks/protron-cannon-indigo"
WT = ROOT = common.repo_root(__file__)
AX = 13.0  # symmetry axis (column edge)

# --- the blueprint's dimensions (sprite px, edge coordinates: c = column edge, v = row edge) ------
BLADE = dict(v0=7.75, v1=15.0, zb=0.35, ze=0.6, ze_in=1.5, zr=3.1, ridge_in=1.3)
TAIL = dict(v0=14.5, v1=21.35, zb=0.4, ze=0.85, zr=1.65, ridge_in=0.85)
COLLAR = dict(v0=16.95, v1=18.0, grow=0.14, lift=0.16)
CORE = dict(nose=9.9, nose_hw=0.85, hw_max=4.0, wide_to=14.1, tail=17.4, slope_f=1.0, slope_r=1.3)
# Front half-width stations: the sprite's nose is 2 px wide on row 10 (only columns 12-13), the
# vanes fill the rest of rows 11-13, so the housing widens late and fast.
CORE_HW = ([9.9, 11.0, 12.0, 13.0, 14.1], [0.8, 1.3, 2.6, 3.6, 4.0])
CROWN = ([9.9, 11.0, 13.4, 15.6, 17.4], [1.75, 2.7, 3.35, 2.85, 1.25])
MUZZLE_Z = 1.05

crown_f = T.pchip(*CROWN)
hw_f = T.pchip(*CORE_HW)


def crown(v):
    return crown_f(min(max(v, CROWN[0][0]), CROWN[0][-1]))


def lerp(a, b, t):
    return a + (b - a) * t


def clamp(x, a, b):
    return max(a, min(b, x))


def mir(side, c):
    return c if side < 0 else 2 * AX - c


def pt(c, v, z):
    """Edge coords to usp_talon's px frame (x = column - 12, y = row, z up)."""
    return (c - 12.0, v, z)


# --- plan functions (left half) -------------------------------------------------------------------

def blade_plan(v):
    return max(3.0, 14.5 - v), (v - 0.5 if v < 11.65 else 22.8 - v)


def tail_plan(v):
    return (4.02 if v < 19 else min(6.98, v - 14.48)), 6.98


def core_hw(v):
    if v < CORE["wide_to"]:
        return min(CORE["hw_max"], hw_f(max(v, CORE["nose"])))
    return max(0.12, CORE["hw_max"] - (v - CORE["wide_to"]) * CORE["slope_r"])


# --- sections ------------------------------------------------------------------------------------

def gable(xo, xi, xr, zb, ze, zr, k, ze_in=None):
    """Chamfered gable section across x (outer -> inner), flat bottom at z 0.05; the outer wall
    ze tall, the inner (root) wall ze_in (a blade thickening toward its root)."""
    ze_in = ze if ze_in is None else ze_in
    w = xi - xo
    c = min(0.32, w * 0.18)
    cb = min(0.35, w * 0.2)
    xr = clamp(xr, xo + c + 0.05, xi - c - 0.05)
    E, Ei, B = ze * k, ze_in * k, zb * k
    R = max(Ei + 0.15, zr * k)
    return [(xo + cb, 0.05), (xo, B), (xo, E), (xo + c, E + c * 0.8), (xr, R),
            (xi - c, Ei + c * 0.8), (xi, Ei), (xi, B), (xi - cb, 0.05)]


def blade_k(v):
    if v < 9.6:
        return lerp(0.55, 1.0, (v - BLADE["v0"]) / (9.6 - BLADE["v0"]))
    if v > 14.7:
        return lerp(1.0, 0.72, (v - 14.7) / 0.3)
    return 1.0


def blade_ring(side, v):
    xo, xi = blade_plan(v)
    s = gable(xo, xi, xi - BLADE["ridge_in"], BLADE["zb"], BLADE["ze"], BLADE["zr"], blade_k(v), BLADE["ze_in"])
    return [pt(mir(side, c), v, z) for c, z in s]


def tail_ring(side, v, grow=0.0, lift=0.0):
    xo, xi = tail_plan(v)
    k = lerp(1.0, 0.6, (v - 19.2) / (TAIL["v1"] - 19.2)) if v > 19.2 else 1.0
    s = gable(xo - grow, xi + grow, xi - TAIL["ridge_in"], TAIL["zb"], TAIL["ze"], TAIL["zr"], k)
    return [pt(mir(side, c), v, z if z == 0.05 else z + lift) for c, z in s]


def core_section(v):
    hw, zc = core_hw(v), crown(v)
    c, f = min(0.3, hw * 0.25), min(0.35, hw * 0.3)
    E = min(1.15, zc - 0.5)
    cr = min(0.32, hw * 0.3)
    return [(-hw + f, 0.0), (-hw, 0.3), (-hw, E), (-hw + c, E + 0.28), (-cr, zc), (cr, zc),
            (hw - c, E + 0.28), (hw, E), (hw, 0.3), (hw - f, 0.0)]


def core_ring(v):
    return [pt(AX + x, v, z) for x, z in core_section(v)]


def core_z(dx, v):
    hw, zc = core_hw(v), crown(v)
    E = min(1.15, zc - 0.5)
    cr = min(0.32, hw * 0.3)
    a = abs(dx)
    if a <= cr:
        return zc
    if a >= hw - 0.3:
        return E + 0.28
    return lerp(zc, E + 0.28, (a - cr) / (hw - 0.3 - cr))


def blade_z(c, v):
    """Top surface of the LEFT vane at column edge c."""
    xo, xi = blade_plan(v)
    xr = clamp(xi - BLADE["ridge_in"], xo + 0.4, xi - 0.4)
    k = blade_k(v)
    e, ei = BLADE["ze"] * k + 0.2, BLADE["ze_in"] * k + 0.2
    if c <= xr:
        return lerp(e, BLADE["zr"] * k, clamp((c - xo) / (xr - xo), 0, 1))
    return lerp(BLADE["zr"] * k, ei, clamp((c - xr) / (xi - xr), 0, 1))


# --- geometry builders ---------------------------------------------------------------------------

def loft(part, rings, mat, cap0=True, cap1=True):
    vr = [[part.v(p) for p in r] for r in rings]
    cents = [tuple(sum(p[i] for p in r) / len(r) for i in range(3)) for r in rings]
    for k, (a, b) in enumerate(zip(vr, vr[1:])):
        n = len(a)
        cen = tuple((cents[k][i] + cents[k + 1][i]) / 2 for i in range(3))
        for i in range(n):
            j = (i + 1) % n
            part.f((a[i], a[j], b[j], b[i]), mat, away=cen)
    if cap0:
        part.f(vr[0], mat, out=(0, -1, 0))
    if cap1:
        part.f(vr[-1], mat, out=(0, 1, 0))


def frame_axes(a, b):
    d = Vector(b) - Vector(a)
    u = d.normalized()
    t = Vector((0, 0, 1)) if abs(u.z) < 0.9 else Vector((1, 0, 0))
    e1 = u.cross(t).normalized()
    e2 = u.cross(e1).normalized()
    return u, e1, e2, d.length


def lathe(part, a, b, profile, mats, sides=14):
    """Revolve `profile` [(r, t)] (t from 0 at a to 1 at b along the axis) round the line a->b.
    mats[i] is the material between profile points i and i + 1. r = 0 closes to the axis."""
    u, e1, e2, L = frame_axes(a, b)
    A = Vector(a)
    rings = []
    for r, t in profile:
        c = A + u * (t * L)
        if r <= 1e-6:
            rings.append(([part.v(tuple(c))], c))
        else:
            rings.append(([part.v(tuple(c + r * (math.cos(q) * e1 + math.sin(q) * e2)))
                           for q in (2 * math.pi * (k + 0.5) / sides for k in range(sides))], c))
    for k, ((r0, c0), (r1, c1)) in enumerate(zip(rings, rings[1:])):
        m = mats[min(k, len(mats) - 1)]
        cen = tuple((c0 + c1) / 2)
        for i in range(sides):
            j = (i + 1) % sides
            if len(r0) == 1 and len(r1) == 1:
                continue
            if len(r0) == 1:
                part.f((r0[0], r1[j], r1[i]), m, out=tuple(-u))
            elif len(r1) == 1:
                part.f((r0[i], r0[j], r1[0]), m, out=tuple(u))
            else:
                # faces between rings at the same t are annular steps: outward along the axis
                if abs(profile[k][1] - profile[k + 1][1]) < 1e-6:
                    out = u if profile[k + 1][0] < profile[k][0] else -u
                    part.f((r0[i], r0[j], r1[j], r1[i]), m, out=tuple(out))
                else:
                    part.f((r0[i], r0[j], r1[j], r1[i]), m, away=cen)


def cyl(part, a, b, r, mat, sides=10):
    lathe(part, a, b, [(0, 0), (r, 0), (r, 1), (0, 1)], [mat], sides)


def ribbon(part, pts, w, h, mat):
    """A groove/seam strip along `pts` (px), w wide, standing h above the given points and sunk
    0.08 below them: modelled panel lines that read as dark seams."""
    rings = []
    for i, p in enumerate(pts):
        p0 = Vector(pts[max(i - 1, 0)])
        p1 = Vector(pts[min(i + 1, len(pts) - 1)])
        d = p1 - p0
        d.z = 0
        if d.length < 1e-9:
            d = Vector((1, 0, 0))
        s = Vector((-d.y, d.x, 0)).normalized() * (w / 2)
        P = Vector(p)
        rings.append([tuple(P - s + Vector((0, 0, -0.08))), tuple(P + s + Vector((0, 0, -0.08))),
                      tuple(P + s + Vector((0, 0, h))), tuple(P - s + Vector((0, 0, h)))])
    vr = [[part.v(q) for q in r] for r in rings]
    for a, b, ra in zip(vr, vr[1:], rings):
        cen = tuple(sum(q[i] for q in ra) / 4 for i in range(3))
        for i in range(4):
            j = (i + 1) % 4
            part.f((a[i], a[j], b[j], b[i]), mat, away=cen)
    part.f(vr[0], mat, away=tuple(Vector(pts[1])))
    part.f(vr[-1], mat, away=tuple(Vector(pts[-2])))


def surface_box(part, cx, v0, v1, w, h, zf, mat):
    """A small block sitting on a surface zf(c, v) (bolt heads, vent bezels), edge coords."""
    corners = [(cx - w / 2, v0), (cx + w / 2, v0), (cx + w / 2, v1), (cx - w / 2, v1)]
    lo = [part.v(pt(c, v, zf(c, v) - 0.15)) for c, v in corners]
    hi = [part.v(pt(c, v, zf(c, v) + h)) for c, v in corners]
    cen = pt(cx, (v0 + v1) / 2, zf(cx, (v0 + v1) / 2) + h / 2)
    for i in range(4):
        j = (i + 1) % 4
        part.f((lo[i], lo[j], hi[j], hi[i]), mat, away=cen)
    part.f(hi, mat, out=(0, 0, 1))
    part.f(lo, mat, out=(0, 0, -1))


# --- the model -----------------------------------------------------------------------------------

def build(sprite, coll):
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(134, metallic=0.6, roughness=0.38),  # 0 vanes (satin steel blue)
        pal(132, metallic=0.6, roughness=0.4),  # 1 spars
        pal(52, metallic=0.5, roughness=0.45),  # 2 clamp bands, knuckles
        pal(53, metallic=0.55, roughness=0.36),  # 3 emitter housing (dark navy)
        pal(59, metallic=0.7, roughness=0.3),  # 4 machined trim: bezel, bolt heads
        pal(57, metallic=0.0, roughness=0.12, emission_strength=0.6),  # 5 emitter lens (glow)
        pal(49, metallic=0.3, roughness=0.6),  # 6 vents, bore, housing seams
        pal(129, metallic=0.5, roughness=0.5),  # 7 vane / spar seams
    ]
    VANE, SPAR, BAND, CORE_M, TRIM, LENS, DARK, SEAM = range(len(mats))
    part = T.Part(NAME + "_A", smooth_angle=32)

    BV = [BLADE["v0"], 8.0, 8.5, 9.0, 9.6, 10.5, 11.0, 11.5, 11.65, 12.2, 12.9, 13.6, 14.3, 14.7, 14.85, BLADE["v1"]]
    TV = [TAIL["v0"], 15.0, 15.8, 16.6, 16.95, 18.0, 18.6, 19.0, 19.5, 20.0, 20.5, 21.0, TAIL["v1"]]
    for side in (-1, 1):
        # Vane and spar.
        loft(part, [blade_ring(side, v) for v in BV], VANE)
        loft(part, [tail_ring(side, v) for v in TV], SPAR)
        # Clamp band: a sleeve standing proud of the spar, its ends chamfered back to the spar.
        cv = [COLLAR["v0"], COLLAR["v0"] + 0.12, COLLAR["v1"] - 0.12, COLLAR["v1"]]
        loft(part, [tail_ring(side, v, *((0.04, 0.02) if i in (0, 3) else (COLLAR["grow"], COLLAR["lift"])))
                    for i, v in enumerate(cv)], BAND)
        # Root hinge knuckle: the vane's pin into the housing flank, half buried.
        ka, kb = (22.5 - 11.75 + 0.15, 11.75), (22.5 - 13.85 + 0.15, 13.85)
        a, b = pt(mir(side, ka[0]), ka[1], 1.35), pt(mir(side, kb[0]), kb[1], 1.35)
        lathe(part, a, b, [(0, 0), (0.3, 0), (0.42, 0.08), (0.42, 0.92), (0.3, 1), (0, 1)], [BAND], sides=10)
        # Root bolt head on the vane: a turned cap standing just proud of the plate.
        bz = blade_z(8.9, 12.85)
        lathe(part, pt(mir(side, 8.9), 12.85, bz - 0.2), pt(mir(side, 8.9), 12.85, bz + 0.1),
              [(0, 0), (0.3, 0), (0.3, 0.75), (0.2, 1), (0, 1)], [TRIM], sides=8)
        # Vane panel seams: one following the swept leading edge 1 px in and down the outer
        # wall's top, one chord-wise across the vane at row 12 (the sprite's mid-blade step).
        lead = []
        v = 8.9
        while v <= 11.5:
            xo, _ = blade_plan(v)
            lead.append(pt(mir(side, xo + 1.0), v, blade_z(xo + 1.0, v)))
            v += 0.26
        v = 11.5
        while v <= 14.6:
            lead.append(pt(mir(side, 4.0), v, blade_z(4.0, v)))
            v += 0.4
        ribbon(part, lead, 0.14, 0.03, SEAM)
        chord = [pt(mir(side, c), 12.0, blade_z(c, 12.0)) for c in [3.3 + 0.4 * i for i in range(12)]]
        ribbon(part, chord, 0.14, 0.03, SEAM)

    # Emitter housing.
    CV = [CORE["nose"], 10.1, 10.6, 11.2, 11.9, 12.6, 13.1, 13.6, 14.1, 14.6, 15.2, 15.8, 16.4, 16.9, 17.3, CORE["tail"]]
    loft(part, [core_ring(v) for v in CV], CORE_M)
    # Girdle seam round the skirt top (both flanks) and a seam across the crown at row 13.4.
    for s in (-1, 1):
        g = []
        v = CORE["nose"] + 0.1
        while v <= CORE["tail"] - 0.1:
            hw = core_hw(v)
            g.append(pt(AX + s * (hw - 0.02), v, min(1.15, crown(v) - 0.5) + 0.12))
            v += 0.25
        ribbon(part, g, 0.12, 0.03, DARK)
    fx = [pt(AX + dx, 13.4, core_z(dx, 13.4)) for dx in [-3.6 + 0.3 * i for i in range(25)]]
    ribbon(part, fx, 0.12, 0.03, DARK)
    # Rear seam across the aft facets at row 15.6 (access panel over the emitter's capacitor bank;
    # no vents: the sprite shows none, and dark slots there read as eyes).
    fx = [pt(AX + dx, 15.6, core_z(dx, 15.6)) for dx in [-2.2 + 0.25 * i for i in range(19)]]
    ribbon(part, fx, 0.12, 0.03, DARK)

    # Muzzle on the flat nose face: a turned bezel (collar, step, lip), a stepped bore and the
    # recessed emitter lens at its bottom, firing north (-v).
    nv, nz = CORE["nose"], MUZZLE_Z
    a, b = pt(AX, nv + 0.2, nz), pt(AX, nv - 0.32, nz)  # a inside the housing, b at the lip
    lathe(part, a, b, [(0, 0), (0.66, 0), (0.66, 0.55), (0.6, 0.62), (0.6, 1.0), (0.42, 1.0),
                       (0.42, 0.78), (0.36, 0.78), (0.36, 0.7), (0, 0.7)],
          [TRIM, TRIM, TRIM, TRIM, TRIM, DARK, DARK, DARK, LENS], sides=14)
    return part, mats


def bake_maps(obj, out_dir, textured, size=512, samples=64, tint=(1.0, 1.0, 1.02)):
    """usp_talon.bake_maps generalised (it hard-codes the Talon's material list): AO at two scales
    with a light edge lift as a colour multiplier, roughness/metalness from occlusion and edges."""
    scene = bpy.context.scene
    try:
        scene.render.engine = "CYCLES"
    except TypeError:
        pass
    scene.cycles.samples = samples
    scene.cycles.device = "CPU"
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
    col_img = bpy.data.images.new("protron_A_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new("protron_A_rm", size // 2, size // 2, alpha=False)
    rm_img.colorspace_settings.name = "Non-Color"
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

        def mth(op, x, y=None):
            n = node("ShaderNodeMath")
            n.operation = op
            for k, val in enumerate((x, y)):
                if val is None:
                    continue
                if isinstance(val, (int, float)):
                    n.inputs[k].default_value = val
                else:
                    nt.links.new(val, n.inputs[k])
            return n.outputs[0]
        # Distances scaled to this small model (a sprite px is 0.083).
        ao_s = node("ShaderNodeAmbientOcclusion")
        ao_s.samples = 24
        ao_s.inputs["Distance"].default_value = 0.02
        ao_l = node("ShaderNodeAmbientOcclusion")
        ao_l.samples = 24
        ao_l.inputs["Distance"].default_value = 0.09
        bev = node("ShaderNodeBevel")
        bev.samples = 8
        bev.inputs["Radius"].default_value = 0.003
        geo = node("ShaderNodeNewGeometry")
        dot = node("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        nt.links.new(bev.outputs["Normal"], dot.inputs[0])
        nt.links.new(geo.outputs["True Normal"], dot.inputs[1])
        edge = mth("MINIMUM", mth("MULTIPLY", mth("SUBTRACT", 1.0, dot.outputs["Value"]), 8.0), 1.0)
        occl = mth("MULTIPLY", mth("POWER", ao_s.outputs["AO"], 0.8),
                   mth("ADD", 0.65, mth("MULTIPLY", ao_l.outputs["AO"], 0.35)))
        em = node("ShaderNodeEmission")
        if mode == "colour":
            val = mth("MINIMUM", mth("ADD", mth("ADD", 0.48, mth("MULTIPLY", occl, 0.62)),
                                     mth("MULTIPLY", edge, 0.2)), 1.0)
            comb = node("ShaderNodeCombineColor")
            for k in range(3):
                nt.links.new(mth("MULTIPLY", val, tint[k]), comb.inputs[k])
        else:
            r = mth("ADD", rough, mth("SUBTRACT", mth("MULTIPLY", mth("SUBTRACT", 1.0, occl), 0.3),
                                      mth("MULTIPLY", edge, 0.16)))
            r = mth("MAXIMUM", mth("MINIMUM", r, 1.0), 0.05)
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
    for i in textured:
        m = mats[i]
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


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    import tempfile
    sprite = common.load_sprite(ROOT, NAME)
    coll = common.reset_collection(NAME)
    part, mats = build(sprite, coll)
    obj = T.finish(part, mats, coll)
    wn = obj.modifiers.new("weighted", "WEIGHTED_NORMAL")
    wn.keep_sharp = True
    wn.weight = 50
    common._apply_modifiers(obj)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"protron: {len(obj.data.polygons)} faces, {tris} triangles")
    fmt = "AUTO"
    if "--no-bake" not in argv:
        bake_dir = Path(tempfile.mkdtemp(prefix="protron_"))
        bake_maps(obj, bake_dir, textured=(0, 1, 2, 3, 4, 6, 7))
        fmt = "WEBP"
    shell = common.outline_shell(obj, coll, voxel=0.008, faces=2000, inside=0.002)
    common.export_sprite_model(ROOT, [obj, shell], MODEL, sprite["sprites"], image_format=fmt)


if __name__ == "__main__":
    main()
