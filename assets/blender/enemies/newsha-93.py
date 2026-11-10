"""newsha-93 / newsha-17 (merged twins): a dome hatch in a segmented collar on rubble.

Reading of the sprite (newsha.shp 93/131 red, 17/55 green, 24x28 px, the whole block painted):
- The block is rubble and sand: island rock from the sprite's own pixels (lib_tiles.sprite_rock, D66),
  a textured sheet at z = 0, no outline (`tyrian_ground`).
- A tan collar (ring) lies on it: outer ellipse centre (12, 13.5) px, 12 x 10.5 px, 2.5 px wide; it
  touches the block's left and right edges. Built as 12 machined, chamfered panels with modelled
  seams over a continuous lower ring. Its darker lower right (230) is shade, so it is symmetric.
- Inside, a dark gutter floor (227) and a glossy red dome (71), base 9.0 x 7.4 px centred
  (12.2, 13.4), on a dark socket band. The dome is 8 petals with fine seams round a hub: an iris.
- At the dome's front foot (cols 8-15, rows 19-21) a small red housing with a dark slot (226).
- Second frame (131 / 55): the iris opens. The petals fold down into a red rim (70) round a tan
  core dome (230) and the collar brightens (235); a ring of glowing vanes (123, emissive) fans out
  round the collar to rows 2..25 (the flare).
Undersides: closed, flat, no detail.

    blender --background --python assets/blender/enemies/newsha-93.py [-- --no-bake]
    (newsha-17.py imports this file and builds the green twin.)

Exports public/models/enemies/<model>.glb + src/render/spriteModels/<model>.json for newsha-93 and
newsha-93-f2 (newsha-17, newsha-17-f2 from newsha-17.py): each a machine object + outline shell +
rock sheet, objects named <model>, <model>_outline, <model>_rock. Coordinates: c / r are sprite px (column, row from
the top-left); X = (c - 12) / 12, Y = (14 - r) / 12, Z = z / 12.
"""

import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector

HERE = Path(__file__).resolve().parent
WT = HERE.parents[2]
sys.path[:0] = [str(WT / "assets" / "blender"), str(WT / "assets" / "blender" / "tiles")]
import common  # noqa: E402
import usp_talon as T  # noqa: E402
import lib_tiles as lt  # noqa: E402

PX = 1 / 12
W, H = 24, 28

# --- palette per model (palette indices from the sprite: medians of each region) ------------------
SCHEMES = {
    "newsha-93": dict(collar=234, collar_lit=235, floor=227, dome=71, rim=70, core=230, housing=71, slot=226,
                      flare=123, frames=(93, 131)),
    "newsha-17": dict(collar=202, collar_lit=206, floor=195, dome=39, rim=38, core=198, housing=39, slot=194,
                      flare=207, frames=(17, 55)),
}

# --- geometry constants (sprite px) ----------------------------------------------------------------
COLLAR = (12.0, 13.5, 12.0, 10.5)      # centre c, r and outer radii
DOME = (12.2, 13.4, 9.0, 7.4)          # dome base ellipse
CORE = (11.8, 13.3, 6.3, 6.2)          # the core dome shown when the iris is open
FLARE = (12.0, 14.45, 13.2, 12.55)     # outer edge of the glowing vanes (frame 2), a superellipse
FLARE_N = 2.25
Z_FLOOR = 0.35
Z_SOCKET = 0.85
DOME_H = 4.9


def X(c):
    return (c - 12) * PX


def Y(r):
    return (14 - r) * PX


def P(c, r, z):
    return (X(c), Y(r), z * PX)


def ell_pt(e, t, d=0.0, s=1.0):
    """Point on ellipse e = (cx, cy, rx, ry) at angle t, scaled by s, offset inward by d px.
    Angle t: 0 = screen right, pi/2 = screen up (row decreasing)."""
    cx, cy, rx, ry = e
    rx, ry = rx * s, ry * s
    x, y = rx * math.cos(t), ry * math.sin(t)
    nx, ny = math.cos(t) / rx, math.sin(t) / ry
    ln = math.hypot(nx, ny)
    x -= d * nx / ln
    y -= d * ny / ln
    return cx + x, cy - y


def arc_speed(e, t):
    _, _, rx, ry = e
    return math.hypot(rx * math.sin(t), ry * math.cos(t))


def sweep(bm, e, profile, t0, t1, steps, mat, closed=False, mode="offset", centre_shift=None):
    """Sweep a closed profile [(u, z)] round ellipse e from angle t0 to t1. mode 'offset': u is an
    inward offset in px; 'scale': u scales the ellipse; 'blend': u in 0..1 blends from e (0) to
    centre_shift (another ellipse, 1). Caps the ends unless closed. Returns the faces."""
    n0 = len(bm.faces)
    ts = [t0 + (t1 - t0) * i / steps for i in range(steps + (0 if closed else 1))]
    rings = []
    for t in ts:
        ring = []
        for u, z in profile:
            if mode == "offset":
                c, r = ell_pt(e, t, d=u)
            elif mode == "scale":
                c, r = ell_pt(e, t, s=u)
            else:
                c0, r0 = ell_pt(e, t)
                c1, r1 = ell_pt(centre_shift, t)
                c, r = c0 + (c1 - c0) * u, r0 + (r1 - r0) * u
            ring.append(bm.verts.new(P(c, r, z)))
        rings.append(ring)
    m = len(profile)
    pairs = list(zip(rings, rings[1:])) + ([(rings[-1], rings[0])] if closed else [])
    for a, b in pairs:
        for k in range(m):
            j = (k + 1) % m
            bm.faces.new((a[k], a[j], b[j], b[k]))
    if not closed:
        bm.faces.new(rings[0])
        bm.faces.new(list(reversed(rings[-1])))
    bm.faces.ensure_lookup_table()
    for f in bm.faces[n0:]:
        f.material_index = mat
    return bm.faces[n0:]


def segments(e, n, gap_px, start=0.0):
    """n angle ranges round ellipse e, separated by seams gap_px wide (measured at the ellipse)."""
    out = []
    for i in range(n):
        a0 = start + 2 * math.pi * i / n
        a1 = start + 2 * math.pi * (i + 1) / n
        g0 = gap_px / 2 / arc_speed(e, a0)
        g1 = gap_px / 2 / arc_speed(e, a1)
        out.append((a0 + g0, a1 - g1))
    return out


def dome_profile(h, z0, s_top, thick, n=9):
    """Outer surface of a dome (scale s from 1 to s_top, pchip-smoothed height), then back down the
    inner surface `thick` px below: a closed petal profile [(s, z)]."""
    ss = [1.0, 0.93, 0.8, 0.6, 0.35, 0.0]
    zz = [0.0, 0.36, 0.62, 0.84, 0.96, 1.0]
    f = T.pchip(ss[::-1], zz[::-1])
    outer = []
    for i in range(n):
        s = 1.0 - (1.0 - s_top) * (i / (n - 1)) ** 0.9
        outer.append((s, z0 + h * f(s)))
    # base chamfer: tuck the foot in a little
    outer[0] = (0.985, z0)
    outer.insert(1, (0.995, z0 + 0.25))
    inner = [(max(s - thick / 9.0, 0.02), z - thick) for s, z in reversed(outer[1:])]
    inner[-1] = (inner[-1][0], z0)
    return outer + inner


def build_machine(name, sch, lit, coll):
    tag = name + ('-f2' if lit else '')
    pal = lambda i, **kw: common.palette_material(SPRITE[name], i, tag, **kw)  # noqa: E731
    mats = [
        pal(sch["collar_lit"] if lit else sch["collar"], metallic=0.55, roughness=0.42),   # 0 collar
        pal(sch["floor"], metallic=0.3, roughness=0.75),                                     # 1 gutter/socket
        pal(sch["dome"], metallic=0.4, roughness=0.22),                                      # 2 dome petals
        pal(sch["core"], metallic=0.55, roughness=0.25),                                     # 3 core
        pal(sch["housing"], metallic=0.4, roughness=0.4),                                    # 4 housing
        pal(sch["slot"], metallic=0.2, roughness=0.8),                                       # 5 slot
        pal(sch["flare"], metallic=0.2, roughness=0.4, emission_strength=2.5),               # 6 flare (lit)
        pal(sch["rim"], metallic=0.4, roughness=0.3),                                        # 7 rim (lit)
    ]
    COL, FLOOR, DOMEM, COREM, HOUS, SLOT, FLAREM, RIMM = range(8)
    bm = bmesh.new()

    # 1. Gutter floor: a disc filling the collar, under everything (ties the parts into one shell).
    sweep(bm, COLLAR, [(0.9, 0.0), (0.9, Z_FLOOR), (0.001, Z_FLOOR), (0.001, 0.0)], 0, 2 * math.pi, 64,
          FLOOR, closed=True, mode="scale")

    # 2. Collar: a continuous lower ring and 12 chamfered panels with seams between them.
    lower = [(0.25, 0.0), (0.3, 1.15), (2.35, 1.15), (2.4, 0.0)]
    sweep(bm, COLLAR, lower, 0, 2 * math.pi, 72, COL, closed=True)
    panel = [(0.0, 0.0), (0.12, 0.85), (0.42, 1.42), (0.78, 1.72), (1.9, 1.72), (2.22, 1.45),
             (2.45, 0.9), (2.55, Z_FLOOR), (2.55, 0.0)]
    for a0, a1 in segments(COLLAR, 12, 0.32, start=math.radians(15)):
        sweep(bm, COLLAR, panel, a0, a1, 8, COL)
    # machined detail: a bolt head at each panel's middle, on the top flat
    for i in range(12):
        t = math.radians(15) + 2 * math.pi * (i + 0.5) / 12
        c, r = ell_pt(COLLAR, t, d=1.34)
        bolt(bm, c, r, 1.72, 0.32, 0.18, COL)

    if not lit:
        # 3. Socket band and the iris dome: 8 petals round a hub, over a core.
        sweep(bm, DOME, [(0.96, Z_FLOOR - 0.05), (0.975, Z_SOCKET), (0.85, Z_SOCKET), (0.85, Z_FLOOR - 0.05)],
              0, 2 * math.pi, 48, FLOOR, closed=True, mode="scale")
        core = [(0.93, Z_SOCKET - 0.1), (0.93, Z_SOCKET + 0.3)] + \
               [(0.93 * math.cos(a), Z_SOCKET + 0.3 + (DOME_H - 0.7) * math.sin(a))
                for a in np.linspace(0.15, math.pi / 2 - 0.05, 7)] + [(0.001, Z_SOCKET + 0.3 + DOME_H - 0.7)]
        core = core + [(0.001, Z_SOCKET - 0.1)]
        sweep(bm, DOME, core, 0, 2 * math.pi, 40, COREM, closed=True, mode="scale")
        prof = dome_profile(DOME_H, Z_SOCKET, 0.17, 0.45)
        for a0, a1 in segments(DOME, 8, 0.26, start=math.radians(22.5)):
            sweep(bm, DOME, prof, a0, a1, 10, DOMEM, mode="scale")
        # hub cap at the crown
        z_top = Z_SOCKET + DOME_H
        hub = [(0.001, z_top - 0.6), (0.2, z_top - 0.6), (0.2, z_top + 0.02), (0.16, z_top + 0.16),
               (0.001, z_top + 0.2)]
        sweep(bm, DOME, hub, 0, 2 * math.pi, 20, DOMEM, closed=True, mode="scale")
    else:
        # 3'. Open iris: socket band, the 8 petals folded down into a rim, and the core risen.
        sweep(bm, DOME, [(0.96, Z_FLOOR - 0.05), (0.975, Z_SOCKET), (0.6, Z_SOCKET), (0.6, Z_FLOOR - 0.05)],
              0, 2 * math.pi, 48, FLOOR, closed=True, mode="scale")
        rim = [(0.0, Z_FLOOR), (0.0, 1.55), (0.12, 2.3), (0.45, 2.85), (0.85, 2.75), (1.0, 2.35), (1.0, Z_FLOOR)]
        for a0, a1 in segments(DOME, 8, 0.3, start=math.radians(22.5)):
            sweep(bm, DOME, rim, a0, a1, 8, RIMM, mode="blend", centre_shift=CORE)
        core_h = 3.7
        core = [(1.0, Z_FLOOR), (1.0, 2.4), (0.985, 2.6)] + \
               [(0.97 * math.cos(a), 2.6 + core_h * math.sin(a)) for a in np.linspace(0.12, math.pi / 2 - 0.04, 8)] + \
               [(0.001, 2.6 + core_h), (0.001, Z_FLOOR)]
        sweep(bm, CORE, core, 0, 2 * math.pi, 40, COREM, closed=True, mode="scale")
        # a machined groove ring round the core at the rim's height
        sweep(bm, CORE, [(1.0, 2.75), (1.03, 2.82), (1.03, 3.02), (1.0, 3.1), (0.9, 3.1), (0.9, 2.75)],
              0, 2 * math.pi, 40, COREM, closed=True, mode="scale")
        # 4'. The flare: 20 glowing vanes fanning out under the collar's outer wall.
        for a0, a1 in segments(FLARE, 20, 0.45, start=math.radians(9)):
            steps = 4
            ts = [a0 + (a1 - a0) * i / steps for i in range(steps + 1)]
            rings = []
            for t in ts:
                ci, ri = ell_pt(COLLAR, t, d=0.7)
                ct, st = math.cos(t), math.sin(t)
                co = FLARE[0] + FLARE[2] * math.copysign(abs(ct) ** (2 / FLARE_N), ct)
                ro = FLARE[1] - FLARE[3] * math.copysign(abs(st) ** (2 / FLARE_N), st)
                # don't let a vane run out of the block
                co = min(max(co, 0.05), 23.95)
                ro = min(max(ro, 0.05), 27.95)
                rings.append([bm.verts.new(P(ci, ri, 1.25)), bm.verts.new(P(co, ro, 0.35)),
                              bm.verts.new(P(co, ro, 0.05)), bm.verts.new(P(ci, ri, 0.85))])
            n0 = len(bm.faces)
            for a, b in zip(rings, rings[1:]):
                for k in range(4):
                    j = (k + 1) % 4
                    bm.faces.new((a[k], a[j], b[j], b[k]))
            bm.faces.new(rings[0])
            bm.faces.new(list(reversed(rings[-1])))
            bm.faces.ensure_lookup_table()
            for f in bm.faces[n0:]:
                f.material_index = FLAREM

    # 5. Front housing with its dark slot (both frames), built with usp_talon's chamfered hulls.
    part = T.Part(f"{name}_housing")
    for x0, x1 in ((7.9, 10.1), (13.9, 16.1)):
        T.hull(part, T.cbox(x0 - 12, x1 - 12, 18.6, 21.75, Z_FLOOR - 0.05, 2.05, 0.3, 0.25), HOUS)
    T.hull(part, T.cbox(10.0 - 12, 14.0 - 12, 18.6, 20.6, Z_FLOOR - 0.05, 2.05, 0.25, 0.2), HOUS)
    T.hull(part, T.cbox(10.0 - 12, 14.0 - 12, 20.4, 21.7, Z_FLOOR - 0.05, 0.95, 0.12, 0.1), SLOT)
    hous = T.finish(part, mats, coll)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.from_mesh(hous.data)  # the housing (already oriented, same material slots)
    hd = hous.data
    bpy.data.objects.remove(hous, do_unlink=True)
    bpy.data.meshes.remove(hd)
    me = bpy.data.meshes.new(f"{name}{'-f2' if lit else ''}")
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    obj = bpy.data.objects.new(me.name, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(32))
    return obj


def bolt(bm, c, r, z, rad, h, mat, sides=8):
    ring0 = [bm.verts.new(P(c + rad * math.cos(2 * math.pi * k / sides), r - rad * math.sin(2 * math.pi * k / sides), z - 0.05))
             for k in range(sides)]
    ring1 = [bm.verts.new(P(c + rad * 0.8 * math.cos(2 * math.pi * k / sides),
                            r - rad * 0.8 * math.sin(2 * math.pi * k / sides), z + h)) for k in range(sides)]
    n0 = len(bm.faces)
    for k in range(sides):
        j = (k + 1) % sides
        bm.faces.new((ring0[k], ring0[j], ring1[j], ring1[k]))
    bm.faces.new(list(reversed(ring0)))
    bm.faces.new(ring1)
    bm.faces.ensure_lookup_table()
    for f in bm.faces[n0:]:
        f.material_index = mat


# --- AO / roughness bake (copied from usp_talon.bake_maps via assembly-newsh2-115.py; all
# non-emissive palette materials textured, neutral tint) -------------------------------------------
TINT = (1.0, 1.0, 1.0)


def bake_maps(obj, out_dir, tag, size=1024, samples=64):
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
        print("no GPU bake", err)
    me = obj.data
    uv = me.uv_layers.new(name="bake")
    me.uv_layers.active = uv
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.003, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.002)
    bpy.ops.object.mode_set(mode="OBJECT")
    col_img = bpy.data.images.new(f"{tag}_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new(f"{tag}_rm", size // 2, size // 2, alpha=False)
    rm_img.colorspace_settings.name = "Non-Color"
    mats = list({m.name: m for m in me.materials}.values())
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

        def math_(op, a, bb=None):
            n = node("ShaderNodeMath")
            n.operation = op
            for k, v in enumerate((a, bb)):
                if v is None:
                    continue
                if isinstance(v, (int, float)):
                    n.inputs[k].default_value = v
                else:
                    nt.links.new(v, n.inputs[k])
            return n.outputs[0]
        ao_s = node("ShaderNodeAmbientOcclusion")
        ao_s.samples = 24
        ao_s.inputs["Distance"].default_value = 0.03
        ao_l = node("ShaderNodeAmbientOcclusion")
        ao_l.samples = 24
        ao_l.inputs["Distance"].default_value = 0.16
        bev = node("ShaderNodeBevel")
        bev.samples = 8
        bev.inputs["Radius"].default_value = 0.005
        geo = node("ShaderNodeNewGeometry")
        dot = node("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        nt.links.new(bev.outputs["Normal"], dot.inputs[0])
        nt.links.new(geo.outputs["True Normal"], dot.inputs[1])
        edge = math_("MINIMUM", math_("MULTIPLY", math_("SUBTRACT", 1.0, dot.outputs["Value"]), 8.0), 1.0)
        occl = math_("MULTIPLY", math_("POWER", ao_s.outputs["AO"], 0.8),
                     math_("ADD", 0.65, math_("MULTIPLY", ao_l.outputs["AO"], 0.35)))
        em = node("ShaderNodeEmission")
        if mode == "colour":
            v = math_("MINIMUM", math_("ADD", math_("ADD", 0.48, math_("MULTIPLY", occl, 0.62)),
                                       math_("MULTIPLY", edge, 0.2)), 1.0)
            tint = node("ShaderNodeCombineColor")
            for k in range(3):
                nt.links.new(math_("MULTIPLY", v, TINT[k]), tint.inputs[k])
            nt.links.new(tint.outputs[0], em.inputs["Color"])
        else:
            r = math_("ADD", rough, math_("SUBTRACT", math_("MULTIPLY", math_("SUBTRACT", 1.0, occl), 0.3),
                                          math_("MULTIPLY", edge, 0.16)))
            r = math_("MAXIMUM", math_("MINIMUM", r, 1.0), 0.05)
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
        bpy.ops.object.bake(type="EMIT", margin=6, use_clear=True)
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
        if bsdf.inputs["Emission Strength"].default_value > 0:
            continue  # glowing parts stay flat palette colour
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


SPRITE = {}


def frames_subset(sprite, frames):
    out = []
    for sp in sprite["sprites"]:
        keep = [f for f in sp["frames"] if f in frames]
        if keep:
            out.append({**sp, "frames": keep})
    return out


def main(names=("newsha-93",)):
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out_dir = Path(argv[argv.index("--out-dir") + 1]) if "--out-dir" in argv else None
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    coll = common.reset_collection("newsha93")
    machines = []
    for name in names:
        sch = SCHEMES[name]
        SPRITE[name] = common.load_sprite(WT, name)
        for k, lit in enumerate((False, True)):
            model = name + ("-f2" if lit else "")
            obj = build_machine(name, sch, lit, coll)
            obj.name = model
            obj["tyrian_model"] = model
            obj["tyrian_frame"] = sch["frames"][k]
            grid = np.array(SPRITE[name]["frames"][k]["pixels"], dtype=np.int32)
            rock = lt.build_sprite_rock(WT, [obj], [(name, 0, 0)], W, H, coll, f"{model}_rock", grid=grid)[name]
            rock.name = f"{model}_rock"
            rock["tyrian_model"] = model
            machines.append((name, model, sch["frames"][k], obj, rock))
            print(f"{model}: {sum(len(p.vertices) - 2 for p in obj.data.polygons)} triangles")
    fmt = "AUTO"
    if "--no-bake" not in argv:
        bake_dir = tempfile.mkdtemp(prefix="newsha_bake_")
        for _, model, _, obj, _ in machines:
            bake_maps(obj, bake_dir, model.replace("-", "_"))
        fmt = "WEBP"
    for name, model, frame, obj, rock in machines:
        shell = common.outline_shell(obj, coll, voxel=0.014, faces=3500)
        shell.name = f"{model}_outline"
        shell["tyrian_model"] = model
        shell.parent = obj
        rock.parent = obj
        if out_dir:
            common.export_glb([obj, shell, rock], out_dir / f"{model}.glb", image_format=fmt)
        else:
            common.export_sprite_model(WT, [obj, shell, rock], f"enemies/{model}",
                                       frames_subset(SPRITE[name], [frame]), image_format=fmt)


if __name__ == "__main__":
    main(("newsha-93",))
