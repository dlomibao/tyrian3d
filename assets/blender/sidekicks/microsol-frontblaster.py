"""MicroSol FrontBlaster (sidekicks 20, 22, 26; tyrian.shp#9 frame 83, 24x28, one frame).

What it is: a front-mounted gun drone (style 2, flies 20 px ahead of the ship). A horseshoe YOKE
(the arch across the front with round 45-degree shoulders, two swept PRONGS running back), twin
round GUN PODS on the arch with dark bores facing north, a dark SLOT between them tied by two
braces, red LAMPS in raised housings on the shoulders, a faceted BRONZE reactor CONE lying on the
axis (tip forward between the pods' breeches, its rear a nozzle overhanging the yoke) and a red
TAIL LAMP on each prong behind a dark seam groove.

Angle: silhouette and readability at the tilted game camera first. The plan follows the
sprite's INNER mask (D74: the game's ink stands in for the sprite's border ring), the heights are
stepped so the pods and cone stand clear of the deck, the lamps are emissive glass that reads at
20 px, and the tail lamps sit on wedges sloping aft so the tilted camera (from the south) sees them.

Authoring units: sprite px. c = column edge (0..24), r = row edge (0..28, south positive), z up.
Mirror axis c = 13. usp_talon.finish maps (x = c - 12, y = r, z) to Blender (x/12, (14 - y)/12,
z/12): the same origin as assets/blender/sidekicks/microsol-frontblaster.py's wx/wy.

Exports public/models/sidekicks/microsol-frontblaster.glb and its spriteModels JSON
(common.export_sprite_model, "ungrouped" kept, D49), AO/roughness bake only (D65), outline shell (D51).

    tools/build-models.sh -j 2 assets/blender/sidekicks/microsol-frontblaster.py
    Blender --background --factory-startup --python microsol-frontblaster.py -- [--no-bake] [--measure DIR]
"""

import json
import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

NAME = "sidekick-microsol-frontblaster"  # object name, reference folder and sprite name
MODEL = "sidekicks/microsol-frontblaster"
ROOT = common.repo_root(__file__)
WT = ROOT
PX = 1 / 12
AX = 13.0  # mirror axis (column edge)
W, H = 24, 28

# Palette index per part: the median of the sprite pixels the part covers seen from above, the
# darkest shading and 13-15 sheen left out as lighting (measured with --measure; see the sheet).
PAL = {
    "yoke": 9, "cap": 8, "prong": 7, "seam": 4, "belly": 5,
    "pod": 11, "pod_seam": 6, "shroud": 9, "lip": 106, "bore": 3, "throat": 1,
    "slot": 1, "brace_a": 9, "brace_b": 10,
    "housing": 10, "lens": 115, "core": 119,
    "cone": 23, "collar": 23, "nozzle": 18,
    "tail_housing": 13, "tail_lens": 118, "tail_glass": 92,
}
GLOW = {"lens": 1.2, "core": 2.0, "tail_lens": 1.4}
FINISH = {  # (metallic, roughness): satin metal, glass
    "pod": (0.6, 0.34), "shroud": (0.55, 0.4), "cone": (0.62, 0.38), "collar": (0.6, 0.4),
    "bore": (0.2, 0.7), "throat": (0.0, 0.9), "slot": (0.3, 0.6), "seam": (0.3, 0.6),
    "lens": (0.0, 0.12), "tail_glass": (0.0, 0.1), "core": (0.0, 0.1), "tail_lens": (0.0, 0.12),
}


def materials(sprite):
    mats, slot = [], {}
    for key, idx in PAL.items():
        met, rough = FINISH.get(key, (0.55, 0.42))
        m = common.palette_material(sprite, idx, f"{NAME}_{key}", metallic=met, roughness=rough,
                                    emission_strength=GLOW.get(key, 0.0))
        slot[key] = len(mats)
        mats.append(m)
    return mats, slot


# --- geometry helpers (sprite px; P space x = c - 12, y = r, z) ------------------------------------

def V(P, c, r, z):
    return P.v((c - 12.0, r, z))


def area(poly):
    return 0.5 * sum(c0 * r1 - c1 * r0 for (c0, r0), (c1, r1) in zip(poly, poly[1:] + poly[:1]))


def edge_out(poly):
    """Outward unit normal (dc, dr) of each edge i -> i+1."""
    s = 1 if area(poly) > 0 else -1
    out = []
    for (c0, r0), (c1, r1) in zip(poly, poly[1:] + poly[:1]):
        dc, dr = c1 - c0, r1 - r0
        ln = math.hypot(dc, dr) or 1e-9
        # for a positive-area loop in (c, r) the outward normal of (dc, dr) is (dr, -dc)
        out.append((s * dr / ln, -s * dc / ln))
    return out


def inset(poly, d):
    """Mitred inward offset by d (negative grows)."""
    en = edge_out(poly)
    n = len(poly)
    res = []
    for i in range(n):
        a, b = en[i - 1], en[i]
        m = (a[0] + b[0], a[1] + b[1])
        ml = math.hypot(*m) or 1e-9
        m = (m[0] / ml, m[1] / ml)
        cos = max(0.35, m[0] * b[0] + m[1] * b[1])
        k = d / cos
        res.append((poly[i][0] - m[0] * k, poly[i][1] - m[1] * k))
    return res


def mirror(poly):
    return [(2 * AX - c, r) for c, r in reversed(poly)]


def plate(P, poly, z0, ztop, mat, ch=0.5, bch=0.0, grooves=(), gd=0.15, top_mat=None):
    """A chamfered plate: outline poly (c, r), bottom z0, top ztop (number or f(c, r)), top chamfer
    ch, bottom chamfer bch, and modelled grooves (a 45-degree V cut gd deep) round the walls at
    the heights in `grooves`."""
    zt = ztop if callable(ztop) else (lambda c, r, v=ztop: v)
    zb = z0 if callable(z0) else (lambda c, r, v=z0: v)
    en = edge_out(poly)
    n = len(poly)
    rings = []  # (points, z or None for top-follow, kind)
    if bch:
        rings.append((inset(poly, bch), zb, "b"))
        rings.append((poly, lambda c, r: zb(c, r) + bch, "w"))
    else:
        rings.append((poly, zb, "w"))
    for g in sorted(grooves):
        rings.append((poly, lambda c, r, g=g: g - gd, "w"))
        rings.append((inset(poly, gd), lambda c, r, g=g: g, "g"))
        rings.append((poly, lambda c, r, g=g: g + gd, "w"))
    if ch:
        rings.append((poly, lambda c, r: zt(c, r) - ch, "w"))
        rings.append((inset(poly, ch), zt, "t"))
    else:
        rings.append((poly, zt, "w"))
    vr = [[V(P, c, r, zf(c, r)) for c, r in pts] for pts, zf, _ in rings]
    for k in range(len(rings) - 1):
        z_dir = {"b": -1, "t": 1}.get(rings[k + 1][2], 0) or {"b": -1}.get(rings[k][2], 0)
        for i in range(n):
            j = (i + 1) % n
            oc, orr = en[i]
            P.f((vr[k][i], vr[k][j], vr[k + 1][j], vr[k + 1][i]), mat, out=(oc, orr, 0.7 * z_dir))
    P.f(list(vr[0]), mat, out=(0, 0, -1))
    P.f(list(vr[-1]), top_mat if top_mat is not None else mat, out=(0, 0, 1))


def lathe(P, c, zc, profile, n, k=1.0, phase=0.0, flip=False):
    """A surface of revolution about the north-south axis at (c, zc): profile [(r, radius, mat)],
    each segment taking the material of its first point; radius 0 is a pole. k scales the vertical
    radius (elliptic). Outward normal of segment (dr, drad) is (drad, -dr) in (r, radius)."""
    angs = [2 * math.pi * (i + phase) / n for i in range(n)]
    rings = []
    for r, rad, _ in profile:
        if rad < 1e-6:
            rings.append([V(P, c, r, zc)])
        else:
            rings.append([V(P, c + rad * math.cos(a), r, zc + k * rad * math.sin(a)) for a in angs])
    for s in range(len(profile) - 1):
        (r0, a0, m), (r1, a1, _) = profile[s], profile[s + 1]
        n_r, n_rad = (a1 - a0), -(r1 - r0)
        if flip:  # a profile running north to south
            n_r, n_rad = -n_r, -n_rad
        R0, R1 = rings[s], rings[s + 1]
        for i in range(n):
            j = (i + 1) % n
            a = (angs[i] + angs[j]) / 2 if j else (angs[i] + angs[j] + 2 * math.pi) / 2
            out = (n_rad * math.cos(a), n_r, n_rad * math.sin(a))
            if len(R0) == 1:
                P.f((R0[0], R1[i], R1[j]), m, out=out)
            elif len(R1) == 1:
                P.f((R0[i], R0[j], R1[0]), m, out=out)
            else:
                P.f((R0[i], R0[j], R1[j], R1[i]), m, out=out)


def box(P, c0, c1, r0, r1, z0, z1, mat, ch=0.2):
    plate(P, [(c0, r0), (c1, r0), (c1, r1), (c0, r1)], z0, z1, mat, ch=ch)


# --- the drone --------------------------------------------------------------------------------------

DECK = 2.0  # yoke top, px
POD_C, POD_Z = 10.5, 3.45  # gun pod axis (column edge, height)
CONE_Z = 2.8


def prong_top(c, r):
    """The prong's top slopes down aft from the seam (swept blades)."""
    return DECK - max(0.0, r - 14.8) * 0.15


def build(P, S):
    # Yoke: one chamfered plate, the arch across the front (45-degree shoulders, rounded), the prong
    # roots down to row 15.2, the rear edge at row 14 between the prongs. Groove round the walls.
    archL = [(7.85, 5.0), (7.45, 5.08), (4.1, 8.35), (4.0, 8.75), (4.0, 15.2), (7.0, 15.2),
             (7.03, 15.0), (7.6, 14.6), (8.1, 14.22), (8.55, 14.0)]
    # archL runs front-centre -> shoulder -> prong root -> rear-centre; close it via the mirror.
    arch = [(c, r) for c, r in archL] + [(2 * AX - c, r) for c, r in reversed(archL)]
    plate(P, arch, -0.8, DECK, S["yoke"], ch=0.55, bch=0.45, grooves=(0.55,))
    # Belly keel (underside: a plain closed shape).
    plate(P, [(7.0, 6.5), (19.0, 6.5), (20.5, 8.5), (20.5, 13.5), (5.5, 13.5), (5.5, 8.5)],
          -1.5, -0.5, S["belly"], ch=0.0, bch=0.35)

    for side in (1, -1):
        M = (lambda pts: pts) if side == 1 else mirror

        # Prong blade: from the seam to the swept tip, top sloping down aft.
        prong = [(4.0, 14.8), (7.0, 14.8), (7.0, 20.72), (6.92, 21.0), (6.6, 21.02), (4.0, 18.55)]
        plate(P, M(prong), lambda c, r: -0.7 + max(0.0, r - 15.5) * 0.12, prong_top, S["prong"],
              ch=0.45, bch=0.4)
        # Seam groove (row 15, the sprite's dark band): a dark insert sunk between the caps.
        plate(P, M([(4.35, 14.55), (6.75, 14.55), (6.75, 15.55), (4.35, 15.55)]), 1.0, DECK + 0.08,
              S["seam"], ch=0.0)
        # Shoulder cap: the armour panel behind the lamp, ahead of the seam.
        cap = [(4.35, 10.55), (8.2, 10.55), (8.2, 13.6), (7.55, 14.3), (7.0, 14.5), (4.35, 14.5)]
        plate(P, M(cap), 1.2, DECK + 0.5, S["cap"], ch=0.25)
        # Aft prong cap, following the blade's slope and taper.
        aft = [(4.35, 15.6), (6.65, 15.6), (6.65, 20.3), (6.47, 20.52), (4.35, 18.4)]
        plate(P, M(aft), 1.0, lambda c, r: prong_top(c, r) + 0.45, S["prong"], ch=0.22)
        # Tail lamp: a wedge housing sloping aft (seen by the tilted camera), red lens on its slope.
        def wedge(c, r, lo=0.25, hi=1.05):
            t = min(1.0, max(0.0, (r - 15.95) / (18.25 - 15.95)))
            return prong_top(c, r) + 0.45 + hi + (lo - hi) * t
        plate(P, M([(4.55, 15.95), (6.45, 15.95), (6.45, 18.25), (4.55, 18.25)]), 1.0, wedge,
              S["tail_housing"], ch=0.22)
        plate(P, M([(4.8, 16.55), (6.2, 16.55), (6.2, 17.95), (4.8, 17.95)]), 1.2,
              lambda c, r: wedge(c, r) + 0.18, S["tail_lens"], ch=0.16)
        # Pale glass strip on the wedge's forward edge (the sprite's lilac pixel above the red lens).
        plate(P, M([(4.8, 16.0), (6.2, 16.0), (6.2, 16.5), (4.8, 16.5)]), 1.2,
              lambda c, r: wedge(c, r) + 0.2, S["tail_glass"], ch=0.1)

        # Shoulder lamp: a raised housing on the arch corner, a big red lens and a hot core.
        hous = [(6.55, 6.25), (8.4, 6.25), (8.4, 10.35), (4.3, 10.35), (4.3, 8.5)]
        plate(P, M(hous), 1.2, 3.3, S["housing"], ch=0.42)
        lens = inset(hous, 0.38)
        plate(P, M(lens), 2.5, 3.85, S["lens"], ch=0.55)
        cc = 6.0 if side == 1 else 2 * AX - 6.0
        plate(P, [(cc - 0.55, 7.95), (cc + 0.55, 7.95), (cc + 0.55, 9.05), (cc - 0.55, 9.05)],
              3.2, 4.12, S["core"], ch=0.2)

        # Gun pod: round housing along the rows, a seam ring at row 9, a gunmetal muzzle shroud with
        # a chamfered lip and a bore; its rear tapers into the deck beside the cone.
        pc = POD_C if side == 1 else 2 * AX - POD_C
        lathe(P, pc, POD_Z, [
            (11.7, 0.0, S["pod"]), (11.3, 0.95, S["pod"]), (10.6, 1.55, S["pod"]), (10.0, 1.8, S["pod"]),
            (9.45, 1.85, S["pod_seam"]), (9.45, 1.68, S["pod_seam"]), (9.0, 1.68, S["pod_seam"]),
            (9.0, 1.85, S["pod"]), (6.6, 1.85, S["pod"]), (6.6, 1.7, S["pod_seam"]), (5.9, 1.7, S["pod_seam"]), (5.9, 1.85, S["pod"]),
            (5.25, 1.85, S["pod"]), (4.95, 1.62, S["shroud"]),
            (4.95, 1.47, S["shroud"]), (4.22, 1.47, S["lip"]), (4.02, 1.25, S["lip"]),
            (4.02, 0.8, S["bore"]), (4.7, 0.8, S["bore"]), (4.7, 0.0, S["throat"]),
        ], 16, k=1.05)

    # Slot between the pods: a dark floor and two braces (the sprite's 9 8 / 10 10 at rows 6, 8).
    box(P, 11.9, 14.1, 5.3, 9.0, 1.0, DECK + 0.22, S["slot"], ch=0.1)
    box(P, 12.05, 13.95, 5.85, 6.75, 2.0, 4.15, S["brace_a"], ch=0.22)
    box(P, 12.05, 13.95, 7.9, 8.95, 2.0, 3.85, S["brace_b"], ch=0.25)

    # Bronze reactor cone: an 8-facet bicone on the axis (a ridge on top), a machined collar at its
    # widest, a nozzle with a dark throat aft. Plan widths fit the sprite's rows 14-17.
    lathe(P, AX, CONE_Z, [
        (8.6, 0.0, S["cone"]), (9.5, 0.75, S["cone"]), (10.0, 1.05, S["cone"]), (11.5, 2.15, S["cone"]), (13.3, 3.85, S["collar"]),
        (13.42, 4.02, S["collar"]), (14.55, 4.02, S["collar"]), (14.67, 3.85, S["cone"]),
        (15.0, 3.55, S["cone"]), (16.5, 2.0, S["cone"]), (17.2, 1.2, S["nozzle"]),
        (17.3, 1.05, S["nozzle"]), (17.95, 1.1, S["nozzle"]), (17.95, 0.68, S["throat"]),
        (17.55, 0.0, S["throat"]),
    ], 8, k=0.78, flip=True)


# --- finishing, bake, measuring ----------------------------------------------------------------------

def bake_maps(obj, out_dir, size=512, samples=64):
    """AO / edge-wear colour multiplier + roughness/metal map ("bake": "model", D65), no concept
    projection. Copied from the dual-shot-option design B (itself from ship-u-ship.py)."""
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
    col_img = bpy.data.images.new(f"{obj.name}_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new(f"{obj.name}_rm", size // 2, size // 2, alpha=False)
    rm_img.colorspace_settings.name = "Non-Color"
    mats = list(me.materials)
    glow = {m.name for m in mats if any(n.type == "BSDF_PRINCIPLED" and n.inputs["Emission Strength"].default_value > 0
                                        for n in m.node_tree.nodes)}
    saved = {}
    for m in mats:
        out = next(n for n in m.node_tree.nodes if n.type == "OUTPUT_MATERIAL")
        saved[m.name] = out.inputs["Surface"].links[0].from_socket if out.inputs["Surface"].links else None

    def bake_shader(m, mode):
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
        ao_s.samples = 24
        ao_s.inputs["Distance"].default_value = 0.02
        ao_l = node("ShaderNodeAmbientOcclusion")
        ao_l.samples = 24
        ao_l.inputs["Distance"].default_value = 0.08
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
        comb = node("ShaderNodeCombineColor")
        if mode == "colour":
            v = math_("MINIMUM", math_("ADD", math_("ADD", 0.48, math_("MULTIPLY", occl, 0.62)),
                                       math_("MULTIPLY", edge, 0.2)), 1.0)
            for k in range(3):
                L(v, comb.inputs[k])
        else:
            r = math_("ADD", rough, math_("SUBTRACT", math_("MULTIPLY", math_("SUBTRACT", 1.0, occl), 0.3),
                                          math_("MULTIPLY", edge, 0.16)))
            r = math_("MAXIMUM", math_("MINIMUM", r, 1.0), 0.05)
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

    for m in mats:
        if m.name in glow:
            continue  # glass keeps its flat palette glow
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


def measure(obj, sprite, out_dir, k=16):
    """A top-view mask render on the sprite's grid (k px per sprite px, Workbench flat) and a raycast
    from above at every sprite pixel centre: the material seen there."""
    from mathutils.bvhtree import BVHTree
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_WORKBENCH"
    except TypeError as err:
        scene.render.engine = next(e for e in str(err).replace("'", " ").replace(",", " ").split() if "WORKBENCH" in e)
    scene.display.shading.light = "FLAT"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_object_outline = False
    scene.display.shading.show_cavity = False
    scene.render.film_transparent = True
    scene.view_settings.view_transform = "Standard"
    scene.render.resolution_x, scene.render.resolution_y = W * k, H * k
    scene.render.resolution_percentage = 100
    cd = bpy.data.cameras.new("mcam")
    cd.type = "ORTHO"
    cd.ortho_scale = H * PX
    cam = bpy.data.objects.new("mcam", cd)
    scene.collection.objects.link(cam)
    cam.location = (0, 0, 5)
    scene.camera = cam
    scene.render.filepath = str(out_dir / "top-83.png")
    bpy.ops.render.render(write_still=True)
    dg = bpy.context.evaluated_depsgraph_get()
    bm = bmesh.new()
    bm.from_object(obj, dg)
    bm.transform(obj.matrix_world)
    bm.faces.ensure_lookup_table()
    tree = BVHTree.FromBMesh(bm)
    grid = []
    for r in range(H):
        row = []
        for c in range(W):
            p = Vector(((c + 0.5 - 12) * PX, (14 - r - 0.5) * PX, 5.0))
            h = tree.ray_cast(p, Vector((0, 0, -1)), 10.0)
            row.append(obj.data.materials[bm.faces[h[2]].material_index].name if h[0] is not None else None)
        grid.append(row)
    bm.free()
    bpy.data.objects.remove(cam, do_unlink=True)
    bpy.context.view_layer.update()
    (out_dir / "raycast.json").write_text(json.dumps({"83": grid}))


def finish(P, mats, coll, name):
    obj = T.finish(P, mats, coll)
    obj.name = name
    return obj


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sprite = common.load_sprite(ROOT, NAME)
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    coll = common.reset_collection(NAME)
    mats, S = materials(sprite)
    P = T.Part(NAME, smooth_angle=34.0)
    build(P, S)
    body = finish(P, mats, coll, NAME)
    T.cull_hidden(body)
    tris = sum(len(p.vertices) - 2 for p in body.data.polygons)
    print(f"{NAME}: {tris} triangles")
    if "--measure" in argv:
        measure(body, sprite, argv[argv.index("--measure") + 1])
    shell = common.outline_shell(body, coll, faces=1200)
    shell.name = f"{NAME}-outline"
    fmt = "AUTO"
    if "--no-bake" not in argv:
        shell.hide_render = True
        bake_maps(body, tempfile.mkdtemp(prefix="msfb_bake_"))
        shell.hide_render = False
        fmt = "WEBP"
    wn = body.modifiers.new("weighted", "WEIGHTED_NORMAL")
    wn.keep_sharp = True
    wn.weight = 50
    common.export_sprite_model(ROOT, [body, shell], MODEL, sprite["sprites"], image_format=fmt)


if __name__ == "__main__":
    main()
