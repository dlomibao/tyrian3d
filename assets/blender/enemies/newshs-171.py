"""Spinning blade (newshs.shp frames 171, 190, 209, 228): a hard-surface twin-ended rotor blade on
a machined hub, the sprite in 3D (M0 shared foundations, D74 inner edge).

A small grey ground object, launched by other enemies (enemy type 455; levels 1.3, 1.6, 1.10, 1.18,
2.3, 3.2). The sprite is a pointed lozenge 12 x 5 px (frames 190 upright and 228 level; 171 and 209
the diagonals), brightest down its centre line: a double-ended steel blade with a ridge along its
length, turning in the ground plane in 45 degree steps. One model per frame (D46): newshs-171
(frame 171, top-left to bottom-right), -f2 (190, upright), -f3 (209, bottom-left to top-right),
-f4 (228, level), the same blade turned and shifted to the frame's measured centre.

Reading of the sprite (tools/calibration/rubric.md): the light centre line (11-12-13) is the ridge
catching the light, the 13s in the middle are sheen on the hub, the darker rim (6-9, 4 and the 32
ink on the diagonals) is the falling-off flank and the ink border, not a dark material. So: one
steel (pal 11) blade with a raised hub; no dark rim is modelled (D74).

Plan (D74, docs/agents/OUTLINE-BORDER.md): half width s * w(d) along the blade (pchip through
W_ST / W_HW, d = distance from the hub in px), tips at T; one shape for all four frames, fitted on
the sprites' inner masks (171 / 209 lose their 32 ink): iou_rule_grid 1.0 on every frame for
s in 0.875-0.912, T in 6.1-6.25; S = 0.893 and T = 6.15 sit mid-window.

Build (sprite px; x across the blade, y along it, z up; to Blender X = x / 12 ...):
- Blade: two arms lofted from the hub out to the tips (pchip stations), a hard twelve-point section:
  a ground cutting edge on the leading side (a narrow bevel to a fine land), flat faces rising to
  a flat ridge down the centre (the sprite's light centre line), a blunt chamfered trailing edge.
  The arms are C2-symmetric (a spinning blade cuts with both arms' leading edges), the section
  symmetric at the hub, so the two arms meet without a seam.
- Root doublers: a chamfered plate over each arm's root on both faces, two rivets each; their
  edges make the panel lines across the blade.
- Hub: a chamfered collar through the blade, a domed cap with a stepped edge, a hex nut and three
  cap screws; the underside is the same hub mirrored (closed, no further detail).
- Texture: AO / roughness bake only (no concept projection), embedded in the GLB.
- Outline shell (common.outline_shell, D51; D90's 0.03 voxels held 0.004 inside).

Run: blender --background --factory-startup --python assets/blender/enemies/newshs-171.py
     [-- --no-bake] [--preview out.png] [--views DIR] [--measure out.json]
Exports public/models/enemies/newshs-171.glb (frame 171) and -f2/-f3/-f4, each with its
src/render/spriteModels entry. --preview renders each frame model beside its sprite (out.png for
frame 171, <name>-f2.png ... next to it); --views writes lit review views and top silhouettes on
the sprite grid; --measure writes the ray-cast top-view coverage per frame.
"""

import json
import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
from usp_talon import Part, pchip, hull  # noqa: E402

NAME = "newshs-171"
REPO = common.repo_root(__file__)
PX = 1 / 12

# --- plan (fitted to the inner masks) --------------------------------------------------------------
S = 0.893
T = 6.15
W_ST = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, T]
W_HW = [S * w for w in (2.45, 2.4, 2.1, 1.6, 1.1, 0.6, 0.0)]
HW = pchip(W_ST, W_HW)
# Half thickness along the blade (px).
TH = pchip([0.0, 1.5, 3.0, 4.5, T], [0.46, 0.43, 0.33, 0.2, 0.05])
Z0 = 1.3  # the blade's mid-plane above the ground (px)

# frame -> (suffix, Blender turn about Z in degrees, centre offset in px (x right, y up))
FRAMES = [(171, "", 45.0, (0.0, 0.0)), (190, "-f2", 0.0, (0.5, 0.0)),
          (209, "-f3", -45.0, (0.0, 0.0)), (228, "-f4", 90.0, (0.0, 0.5))]

M_BLADE, M_EDGE, M_RIDGE, M_HUB, M_CAP, M_NUT, M_RIVET, M_DOUBLER = range(8)
# Palette index per part (D52): the median of the sprite pixels each part covers over all four
# frames, each frame's darkest (4 / 6, and the 32 ink) and brightest (12 / 13) steps left out as
# lighting: the blade 10 (171 / 209 give 9.5, 190 / 228 give 11; all frames 10), the ridge 11, the
# hub collar 11, the cap 12 (its 13s are sheen). The rim's dark pixels are the flank falling away
# from the light, so the cutting edges keep the blade's 10 (no dark rim, D74).
PAL_OF = {M_BLADE: 10, M_EDGE: 10, M_RIDGE: 11, M_HUB: 11, M_CAP: 12, M_NUT: 10, M_RIVET: 11,
          M_DOUBLER: 10}
MAT_ARGS = {M_BLADE: ("blade", 0.5, 0.36), M_EDGE: ("edge", 0.55, 0.28), M_RIDGE: ("ridge", 0.5, 0.32),
            M_HUB: ("hub", 0.45, 0.4), M_CAP: ("cap", 0.5, 0.3), M_NUT: ("nut", 0.45, 0.42),
            M_RIVET: ("rivet", 0.5, 0.34), M_DOUBLER: ("doubler", 0.45, 0.42)}
TINT = (1.0, 1.0, 1.0)


def materials(sprite):
    return [common.palette_material(sprite, PAL_OF[i], f"nshs171_{MAT_ARGS[i][0]}",
                                    metallic=MAT_ARGS[i][1], roughness=MAT_ARGS[i][2])
            for i in range(len(PAL_OF))]


# --- blade ------------------------------------------------------------------------------------------

def section(d, side=1.0):
    """The blade's section at distance d from the hub: [(x, z, mat_of_face_to_next)] round the
    outline, x across (leading edge at +x * side), z about the mid-plane. Hard points; the faces
    between them carry the material of the segment."""
    W = max(HW(d), 0.02)
    t = max(TH(d), 0.03)
    # Asymmetry: 0 under the hub (both arms meet there), easing in to full by d 2.6 (smoothstep,
    # so the leading bevel and trailing chamfer grow out of the collar without a kink).
    a = min(1.0, max(0.0, (d - 0.9) / 1.7))
    a = a * a * (3 - 2 * a)
    def mix(p, q):
        return p + (q - p) * a
    r = min(0.42, 0.3 * W)               # ridge flat half width
    # At the hub both edges are the same blunt chamfered edge (so the two arms meet cleanly);
    # outward the leading side becomes a ground cutting edge (a wide bevel to a fine land) and
    # the trailing side a narrower chamfer to a thicker edge.
    e0, c0, z0 = 0.3 * t, 0.3 * W, 0.72 * t
    lead_e, lead_c, lead_z = mix(e0, 0.06 * t + 0.015), mix(c0, min(0.62, 0.45 * W)), mix(z0, 0.55 * t)
    trail_e, trail_c, trail_z = mix(e0, 0.34 * t), mix(c0, 0.25 * W), mix(z0, 0.62 * t)
    pts = [
        (W, lead_e, M_EDGE),
        (W - lead_c, lead_z, M_BLADE),
        (r, t, M_RIDGE),
        (-r, t, M_BLADE),
        (-(W - trail_c), trail_z, M_BLADE),
        (-W, trail_e, M_BLADE),
        (-W, -trail_e, M_BLADE),
        (-(W - trail_c), -trail_z, M_BLADE),
        (-r, -t, M_BLADE),
        (r, -t, M_BLADE),
        (W - lead_c, -lead_z, M_EDGE),
        (W, -lead_e, M_EDGE),
    ]
    return [(x * side, z, m) for x, z, m in pts]


def build_arm(part, sign):
    """One arm, from the hub (d 0) out to the tip, along y * sign. Leading edge +x for the +y arm;
    the -y arm is the +y arm turned 180 degrees (so its leading edge is -x)."""
    ds = [0.0, 0.5, 0.9, 1.3, 1.7, 2.1, 2.6, 3.0, 3.5, 4.0, 4.4, 4.8, 5.2, 5.5, 5.75, 5.95, 6.08]
    rings = []
    for d in ds:
        sec = section(d)
        ring = []
        for x, z, _m in sec:
            ring.append(part.v((x * sign, d * sign, z)))
        rings.append((ring, [m for _, _, m in sec], d))
    tip = part.v((0.0, T * sign, 0.0))
    for (r0, ms, d0), (r1, _, d1) in zip(rings, rings[1:]):
        n = len(r0)
        for i in range(n):
            j = (i + 1) % n
            part.f((r0[i], r0[j], r1[j], r1[i]), ms[i], away=(0.0, d0 * sign, 0.0))
    r_last, ms, d_last = rings[-1]
    n = len(r_last)
    for i in range(n):
        part.f((r_last[i], r_last[(i + 1) % n], tip), ms[i], away=(0.0, (d_last - 0.4) * sign, 0.0))
    part.f(rings[0][0], M_BLADE, out=(0.0, -sign, 0.0))  # buried in the hub


def surf_z(x, d, top=True):
    """The blade's top (or bottom) surface height at (x across, d along the +y arm)."""
    sec = section(d)
    half = sec[:6] if top else sec[6:]
    pts = sorted((p[0], p[1]) for p in half)
    if x <= pts[0][0]:
        return pts[0][1]
    for (x0, z0), (x1, z1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            return z0 + (z1 - z0) * (x - x0) / max(x1 - x0, 1e-6)
    return pts[-1][1]


def doubler(part, det, sign, top):
    """A chamfered root plate over the arm's root (d 1.75-3.1), 0.09 proud, with two rivets."""
    zs = 1.0 if top else -1.0
    d0, d1 = 1.75, 3.1
    pts = []
    for d in (d0, d0 + 0.12, d1 - 0.12, d1):
        inset = 0.12 if d in (d0, d1) else 0.0
        w = HW(d) - 0.55 - inset
        for x in (-w, -w * 0.5, 0.0, w * 0.5, w):
            z = abs(surf_z(x, d, top))
            pts.append((x, d, zs * (z + 0.09 - (0.06 if inset else 0.0))))
            pts.append((x, d, zs * (z - 0.25)))
        # chamfer at the sides
        for x in (-(w + 0.1), w + 0.1):
            z = abs(surf_z(x, d, top))
            pts.append((x, d, zs * (z - 0.25)))
    pts = [(x * sign, d * sign, z) for x, d, z in pts]
    hull(part, pts, M_DOUBLER)
    for d in (2.15, 2.75):
        z = abs(surf_z(0.0, d, top)) + 0.09
        rv = []
        for k in range(6):
            a = 2 * math.pi * (k + 0.5) / 6
            for rr, h in ((0.17, -0.03), (0.11, 0.09)):
                rv.append((rr * math.cos(a), d * sign + rr * math.sin(a), zs * (z + h)))
        hull(det, rv, M_RIVET)


def ring_pts(r, z, n=16, rot=0.5):
    return [(r * math.cos(2 * math.pi * (k + rot) / n), r * math.sin(2 * math.pi * (k + rot) / n), z)
            for k in range(n)]


def build_hub(part, det, top):
    zs = 1.0 if top else -1.0
    # Collar: a chamfered drum through the blade.
    hull(part, [(x, y, zs * z) for x, y, z in
                ring_pts(1.55, 0.0) + ring_pts(1.55, 0.5) + ring_pts(1.43, 0.62)], M_HUB)
    # Cap: a stepped shoulder and a low dome.
    hull(part, [(x, y, zs * z) for x, y, z in
                ring_pts(1.18, 0.55) + ring_pts(1.18, 0.74) + ring_pts(1.06, 0.8)], M_CAP)
    dome = []
    for r, z in ((1.0, 0.78), (0.86, 0.9), (0.62, 0.98), (0.3, 1.02)):
        dome += ring_pts(r, z)
    hull(part, [(x, y, zs * z) for x, y, z in dome], M_CAP)
    if top:
        # Hex nut and three cap screws round it (top only: the game camera sees the top).
        hull(det, [(x, y, z) for x, y, z in ring_pts(0.42, 0.95, 6, 0.0) + ring_pts(0.42, 1.16, 6, 0.0)
                   + ring_pts(0.34, 1.22, 6, 0.0)], M_NUT)
        for k in range(3):
            a = 2 * math.pi * (k / 3 + 1 / 12)
            cx, cy = 1.32 * math.cos(a), 1.32 * math.sin(a)
            hull(det, [(cx + x, cy + y, z) for x, y, z in ring_pts(0.13, 0.55, 6) + ring_pts(0.1, 0.7, 6)],
                 M_RIVET)
    else:
        hull(det, [(x, y, -z) for x, y, z in ring_pts(0.42, 0.95, 6, 0.0) + ring_pts(0.36, 1.1, 6, 0.0)],
             M_NUT)


def finish(part, mats, coll, name):
    part.orient()
    bm = part.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    m = Matrix(((PX, 0, 0, 0), (0, PX, 0, 0), (0, 0, PX, Z0 * PX), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for mat in mats:
        me.materials.append(mat)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(part.smooth_angle))
    return obj


def build(coll, mats):
    blade = Part("blade", smooth_angle=25.0)
    det = Part("detail", smooth_angle=30.0)
    for sign in (1.0, -1.0):
        build_arm(blade, sign)
        for top in (True, False):
            doubler(det, det, sign, top)
    for top in (True, False):
        build_hub(det, det, top)
    objs = [finish(blade, mats, coll, "blade"), finish(det, mats, coll, "detail")]
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    obj.name = NAME + "_base"
    obj.data.name = NAME + "_base"
    return obj


# --- bake (after newsh2-171 / usp_talon.bake_maps, for this model's materials) ---------------------

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
        print(f"{NAME}: no GPU bake", err)
    me = obj.data
    uv = me.uv_layers.new(name="bake")
    me.uv_layers.active = uv
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.006, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.004)
    bpy.ops.object.mode_set(mode="OBJECT")
    col_img = bpy.data.images.new("nshs171_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new("nshs171_rm", size // 2, size // 2, alpha=False)
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
        L = nt.links.new
        tmp = []

        def node(kind):
            n = nt.nodes.new(kind)
            tmp.append(n)
            return n

        def math_(op, a, b=None):
            n = node("ShaderNodeMath")
            n.operation = op
            for k, val in enumerate((a, b)):
                if val is None:
                    continue
                if isinstance(val, (int, float)):
                    n.inputs[k].default_value = val
                else:
                    L(val, n.inputs[k])
            return n.outputs[0]
        ao_s = node("ShaderNodeAmbientOcclusion")
        ao_s.samples = 24
        ao_s.inputs["Distance"].default_value = 0.012
        ao_l = node("ShaderNodeAmbientOcclusion")
        ao_l.samples = 24
        ao_l.inputs["Distance"].default_value = 0.05
        bev = node("ShaderNodeBevel")
        bev.samples = 8
        bev.inputs["Radius"].default_value = 0.002
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
            val = math_("MINIMUM", math_("ADD", math_("ADD", 0.48, math_("MULTIPLY", occl, 0.62)),
                                         math_("MULTIPLY", edge, 0.2)), 1.0)
            tint = node("ShaderNodeCombineColor")
            for k in range(3):
                L(math_("MULTIPLY", val, TINT[k]), tint.inputs[k])
            L(tint.outputs[0], em.inputs["Color"])
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


# --- frames, measure, views -------------------------------------------------------------------------

def frame_matrix(turn, off):
    return Matrix.Translation((off[0] * PX, off[1] * PX, 0.0)) @ Matrix.Rotation(math.radians(turn), 4, "Z")


def frame_copy(src, name, coll, turn, off, weighted=True):
    me = src.data.copy()
    me.transform(frame_matrix(turn, off))
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    if weighted:
        wn = obj.modifiers.new("weighted", "WEIGHTED_NORMAL")
        wn.keep_sharp = True
        wn.weight = 50
    return obj


def measure(obj, frame, sub=10):
    """Ray-cast top view on the sprite grid: per-pixel coverage, per-material sprite indices."""
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    me = ev.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    tree = BVHTree.FromBMesh(bm)
    mats = [f.material_index for f in bm.faces]
    pix = frame["pixels"]
    H, W = len(pix), len(pix[0])
    cov = [[0.0] * W for _ in range(H)]
    regions = {}
    for r in range(H):
        for c in range(W):
            hits, counts = 0, {}
            for i in range(sub):
                for j in range(sub):
                    u, v = c + (i + 0.5) / sub, r + (j + 0.5) / sub
                    hit = tree.ray_cast(Vector(((u - 6) * PX, (7 - v) * PX, 5.0)), Vector((0, 0, -1)), 20.0)
                    if hit[0] is not None:
                        hits += 1
                        counts[mats[hit[2]]] = counts.get(mats[hit[2]], 0) + 1
            cov[r][c] = hits / sub / sub
            if counts and cov[r][c] >= 0.5 and pix[r][c] >= 0:
                regions.setdefault(max(counts, key=counts.get), []).append(pix[r][c])
    bm.free()
    ev.to_mesh_clear()
    return {"frame": frame["index"], "cov": [[round(x, 2) for x in row] for row in cov],
            "regions": {str(k): v for k, v in regions.items()}}


def setup_render(px_w, px_h, engine="BLENDER_EEVEE_NEXT"):
    scene = bpy.context.scene
    for e in (engine, "BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            scene.render.engine = e
            break
        except TypeError:
            continue
    scene.render.resolution_x, scene.render.resolution_y = px_w, px_h
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.view_settings.view_transform = "Standard"
    if scene.world is None:
        scene.world = bpy.data.worlds.new("w")
    scene.world.use_nodes = True
    bg = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.35, 0.36, 0.4, 1.0)
    bg.inputs[1].default_value = 0.6
    return scene


def add_cam(name, loc, look, ortho):
    data = bpy.data.cameras.new(name)
    data.type = "ORTHO"
    data.ortho_scale = ortho
    cam = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = loc
    cam.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return cam


def render_views(objs, out_dir):
    """Lit views of each frame model (EEVEE, a key light from the upper left as the sprite's) and an
    unlit top silhouette on the sprite grid (k = 20) for tools/sprite_mask.py --measure."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    scene = setup_render(480, 480)
    sun = bpy.data.lights.new("key", "SUN")
    sun.energy = 2.2
    so = bpy.data.objects.new("key", sun)
    scene.collection.objects.link(so)
    so.rotation_euler = (Vector((0.55, -0.5, -1.0))).to_track_quat("-Z", "Y").to_euler()
    fill = bpy.data.lights.new("fill", "SUN")
    fill.energy = 0.8
    fo = bpy.data.objects.new("fill", fill)
    scene.collection.objects.link(fo)
    fo.rotation_euler = (Vector((-0.6, 0.7, -0.4))).to_track_quat("-Z", "Y").to_euler()
    every = [o for o in scene.objects if o.type == "MESH"]
    D = 3.0
    zc = Z0 * PX
    views = {
        "top": ((0, 0, D), (0, 0, 0), 1.25),
        "side": ((D, 0, zc), (0, 0, zc), 1.25),
        "front": ((0, -D, zc), (0, 0, zc), 1.25),
        "rear": ((0, D, zc), (0, 0, zc), 1.25),
        "q34": ((D * 0.62, -D * 0.62, D * 0.62), (0, 0, zc), 1.25),
        "game": ((0, -D * 0.5, D * 0.87), (0, 0, zc), 1.25),
        "under": ((0.001, 0.0, -D), (0, 0, 0), 1.25),
        "close": ((D * 0.5, -D * 0.7, D * 0.5), (0.0, 0.0, zc), 0.7),
    }
    for o in every:
        o.hide_render = True
    for name, obj in objs:
        obj.hide_render = False
        for v, (loc, look, ortho) in views.items():
            if name != NAME and v not in ("top", "game", "q34"):
                continue
            cam = add_cam(f"cam_{v}", loc, look, ortho)
            if v == "top":
                cam.rotation_euler = (0, 0, 0)
            scene.camera = cam
            scene.render.filepath = str(out_dir / f"{name}_{v}.png")
            bpy.ops.render.render(write_still=True)
            bpy.data.objects.remove(cam, do_unlink=True)
        obj.hide_render = True
    # Silhouettes on the sprite grid (12 x 14 px at k = 20), unlit.
    scene.render.resolution_x, scene.render.resolution_y = 240, 280
    cam = add_cam("cam_grid", (0, 0, 3), (0, 0, 0), 14 * PX)
    cam.rotation_euler = (0, 0, 0)
    scene.camera = cam
    for name, obj in objs:
        obj.hide_render = False
        scene.render.filepath = str(out_dir / f"{name}_grid.png")
        bpy.ops.render.render(write_still=True)
        obj.hide_render = True
    for o in every:
        o.hide_render = False


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sprite = common.load_sprite(REPO, NAME)
    coll = common.reset_collection(NAME)
    mats = materials(sprite)
    base = build(coll, mats)
    tris = sum(len(p.vertices) - 2 for p in base.data.polygons)
    print(f"{NAME}: {len(base.data.polygons)} faces, {tris} triangles")
    fmt = "AUTO"
    if "--no-bake" not in argv:
        bake_maps(base, tempfile.mkdtemp(prefix="nshs171_bake_"))
        fmt = "WEBP"
    # D90's shell: 0.03 voxels bridge the seams round the hub, held 0.004 inside (at 0.006 its back
    # faces stood out of them and drew two ink slits beside the hub).
    shell = common.outline_shell(base, coll, voxel=0.03, faces=3000, inside=0.004)
    frames = {f["index"]: f for f in sprite["frames"]}
    objs, info = [], {"triangles": tris, "frames": []}
    for frame, suffix, turn, off in FRAMES:
        name = NAME + suffix
        obj = frame_copy(base, name, coll, turn, off)
        obj["tyrian_frame"] = frame
        sh = frame_copy(shell, f"{name}_outline", coll, turn, off, weighted=False)
        sh["tyrian_outline"] = True
        sh.parent = obj
        sprites = [dict(s, frames=[frame]) for s in sprite["sprites"]]
        common.export_sprite_model(REPO, [obj, sh], f"enemies/{name}", sprites, image_format=fmt)
        objs.append((name, obj))
        if "--measure" in argv:
            info["frames"].append(measure(obj, frames[frame]))
    base.hide_render = True
    shell.hide_render = True
    for o in coll.objects:
        if o.get("tyrian_outline"):
            o.hide_render = True
    if "--measure" in argv:
        out = Path(argv[argv.index("--measure") + 1])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(info, indent=1))
    if "--preview" in argv:
        out = Path(argv[argv.index("--preview") + 1])
        for i, (name, obj) in enumerate(objs):
            f = sprite["frames"][i] if sprite["frames"][i]["index"] == FRAMES[i][0] else frames[FRAMES[i][0]]
            ref = REPO / "reference" / "models" / NAME / f["image"]
            path = out if i == 0 else out.with_name(f"{name}.png")
            common.render_preview([obj], str(path), ref, size=1, frame=f["index"])
    if "--views" in argv:
        render_views(objs, argv[argv.index("--views") + 1])


if __name__ == "__main__":
    main()
