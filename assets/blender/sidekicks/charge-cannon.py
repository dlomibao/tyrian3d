"""Charge Cannon (sidekick option 3, tyrian.shp#8 frames 258-260, 277-279, 296-298): a 3D
version of its sprite to the player-ship hard-surface standard (DECISIONS D50-D53, D65, D74).

What it is: a small mounted side pod (style 0), a blue-steel capsule cannon that charges an exposed
red core cell in its middle and spits blue sparks off it when fully charged.

What the sprite shows (reference/models/sidekick-charge-cannon, 12x14, palette 5; inner mask = what
the top view covers, its ink border left to the game's outline, D74):
- rows 0-2: the muzzle barrel, 6 px wide (cols 3-8), its front edge row 0 (no ink: the front face);
  row 2 a band of its own (it brightens on its own on 278/279);
- row 3: a dark recessed groove ring (52), still 6 px;
- row 4: the front collar flange, 8 px (cols 2-9);
- rows 5 and 8: dark maroon retainer rings (241), 4 px (cols 4-7, the dark 241/224/240 at cols 3/8
  are ink);
- rows 6-7: the core cell, 6 px, red-brown 245 brightening to 247 and 248 through the animation
  (the 253 column at col 4 is sheen on a round drum);
- row 9: the rear body, 6 px; row 10: the rear collar flange, 8 px;
- rows 11-12: the tail: a lit centre spine (cols 5-6), dark vent slots beside it (cols 3-4 on row 11,
  col 4 on row 12) and lit cheeks (col 3/8 on row 12) closing them;
- row 13: a narrower tail cap, 4 px (cols 4-7).
- Charge: frame +1 brightens a band of the steel (nose on 259, band/flange/rear body on 278, rear
  body/flange/spine on 297): palette_material frames=; frame +2 adds four blue spark pixels
  (151/154/157) beside the core: emissive spark parts shown by frame (frame_part).

Design: one closed round revolve (sprite px: x = column - 6, y = row edge, z up, the axis at z 0),
its profile hard-edged where the sprite steps (chamfered collars, a recessed groove, a modelled
panel seam ahead of the band), the core a pchip barrel with two shallow machined grooves, the tail
a dark core under three proud armour plates (spine, cheeks, lower wall) whose gaps are the vent
slots. Machined detail where the cameras see: a recessed muzzle with a glowing emitter lens, bolt
rings on both collars' outer faces, mount lugs low on the flanks, a finned charge vent in the tail
cap. Underside: the same round hull, closed, nothing more.

Run: tools/build-models.sh -j 2 assets/blender/sidekicks/charge-cannon.py\n(--out DIR after -- also writes review renders.) Exports public/models/sidekicks/charge-cannon.glb\nand src/render/spriteModels/charge-cannon.json.
"""

import json
import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

WT = Path("/Users/dlomibao/projects/tyrian-worktrees/sidekicks-2")
sys.path.insert(0, str(WT / "assets" / "blender"))
import common  # noqa: E402
import usp_talon as T  # noqa: E402
from usp_talon import Part, cbox, hull, pchip, frange  # noqa: E402

NAME = "charge-cannon"
REF = f"sidekick-{NAME}"
HERE = Path(__file__).resolve().parent
PX = 1 / 12
N = 24  # segments round the hull

# Material slots.
(NOSE, BAND, GROOVE, FFLANGE, RIM, CORE, RBODY, RFLANGE, SPINE, SLOT, WALL, CAP, BORE, LENS, BOLT,
 SP151, SP154, SP157, ARC, RIM2) = range(20)

ALL = [258, 259, 260, 277, 278, 279, 296, 297, 298]
SPARKS = {  # frame: (row, col, palette index) of the spark pixels
    260: [(5, 0, 157), (6, 10, 154), (7, 2, 151), (8, 11, 157)],
    279: [(6, 1, 154), (6, 9, 151), (7, 10, 154), (8, 0, 157)],
    298: [(5, 11, 157), (6, 2, 151), (7, 1, 154), (7, 9, 151)],
}


def materials(sprite):
    def steel(i, tag, frames=None, rough=0.4, metal=0.32):
        return common.palette_material(sprite, i, f"cc_{tag}", metallic=metal, roughness=rough, frames=frames)

    def glow(i, tag, e, rough=0.4):
        return common.palette_material(sprite, i, f"cc_{tag}", metallic=0.0, roughness=rough, emission_strength=e)
    # Palette index per part: the median of the sprite pixels it covers (the 48 ink, darkest shading and
    # brightest highlights left out), per frame where the charge brightens it.
    return [
        steel(58, "nose", {259: 61, 260: 61}),
        steel(58, "band", {259: 60, 260: 60, 278: 60, 279: 60}),
        steel(52, "groove", rough=0.5),
        steel(58, "fflange", {278: 61, 279: 61}, rough=0.36),
        steel(241, "rim", rough=0.42, metal=0.4),
        common.palette_material(sprite, 246, "cc_core", metallic=0.35, roughness=0.26, emission_strength=0.4,
                                frames={277: 247, 278: 247, 279: 247, 296: 248, 297: 248, 298: 248}),
        steel(58, "rbody", {278: 60, 279: 60, 297: 60, 298: 60}),
        steel(59, "rflange", {297: 61, 298: 61}, rough=0.36),
        steel(60, "spine", {297: 61, 298: 61}, rough=0.36),
        steel(53, "slot", rough=0.55),
        steel(59, "wall"),
        steel(54, "cap"),
        common.palette_material(sprite, 48, "cc_bore", metallic=0.1, roughness=0.8),
        glow(154, "lens", 0.9, rough=0.15),
        steel(56, "bolt", rough=0.3, metal=0.4),
        glow(151, "spark151", 1.3),
        glow(154, "spark154", 1.3),
        glow(157, "spark157", 1.1),
        glow(157, "arc", 1.1),
        steel(243, "rim_rear", rough=0.42, metal=0.4),
    ]


# --- geometry helpers (sprite px) ---------------------------------------------------------------

def ring(part, y, r, n=N, phase=0.0):
    if r <= 1e-6:
        return [part.v((0.0, y, 0.0))]
    return [part.v((r * math.sin(phase + 2 * math.pi * i / n), y, r * math.cos(phase + 2 * math.pi * i / n)))
            for i in range(n)]


def revolve(part, prof, n=N):
    """A closed solid of revolution round the y axis. `prof` is [(y, r, mat)] from the front axis
    to the rear axis along the surface; mat colours the segment to the next point. Each face is
    oriented by the profile's outward normal (so steps and recesses face the right way)."""
    rings = [ring(part, y, r, n) for y, r, _ in prof]
    for k in range(len(prof) - 1):
        (y0, r0, m), (y1, r1, _) = prof[k], prof[k + 1]
        ny, nr = -(r1 - r0), (y1 - y0)   # outward normal in the (y, r) plane
        a, b = rings[k], rings[k + 1]
        for i in range(n):
            j = (i + 1) % n
            ang = 2 * math.pi * (i + 0.5) / n
            out = (nr * math.sin(ang), ny, nr * math.cos(ang))
            if len(a) == 1:
                part.f((a[0], b[i], b[j]), m, out=out)
            elif len(b) == 1:
                part.f((a[i], a[j], b[0]), m, out=out)
            else:
                part.f((a[i], a[j], b[j], b[i]), m, out=out)


def circle_loop(r):
    def f(y):
        return [(r * math.sin(2 * math.pi * i / N), r * math.cos(2 * math.pi * i / N)) for i in range(N)], (0.0, 0.0)
    return f


def bolt(part, centre, axis, rad=0.17, h=0.13, mat=BOLT):
    """A hex bolt head standing h along axis (+-y) from centre."""
    cx, cy, cz = centre
    pts = []
    for k in range(6):
        t = 2 * math.pi * k / 6
        for dy, rr in ((-0.05, rad), (h * 0.7, rad), (h, rad * 0.75)):
            pts.append((cx + rr * math.cos(t), cy + axis * dy, cz + rr * math.sin(t)))
    hull(part, pts, mat)


# --- the body ----------------------------------------------------------------------------------

RIM_R = 2.15     # retainer rings (rows 5 and 8): the inner mask's 4 px
BODY_R = 3.0     # the barrel and rear body (6 px)
FLANGE_R = 4.05  # the collars (8 px)
TAIL_R = 2.75    # the tail's dark core under its plates
CAP_R = 2.05     # tail cap (row 13: 4 px)


def core_profile():
    """The core cell between the retainer rings: a pchip barrel, rows 5.5-8.5, two shallow
    machined grooves round it."""
    ys = [5.66, 5.8, 6.02, 6.3, 7.7, 7.98, 8.2, 8.34]
    rs = [RIM_R, 2.55, 2.9, BODY_R, BODY_R, 2.9, 2.55, RIM_R]
    f = pchip(ys, rs)
    final = [(y, f(y), CORE) for y in frange(5.66, 8.34, 0.15)
             if not any(abs(y - g) < 0.12 for g in (6.6, 7.4))]
    for g in (6.6, 7.4):
        final += [(g - 0.07, BODY_R, CORE), (g - 0.03, BODY_R - 0.1, CORE), (g + 0.03, BODY_R - 0.1, CORE),
                  (g + 0.07, BODY_R, CORE)]
    final.sort(key=lambda p: p[0])
    return final


def body_profile():
    P = []
    # Muzzle: the emitter lens dome in the bore, the bore floor and wall, a chamfered lip.
    P += [(0.52, 0.0, LENS), (0.56, 0.42, LENS), (0.66, 0.78, LENS), (0.74, 0.98, BORE), (0.74, 1.3, BORE),
          (0.12, 1.3, NOSE), (0.0, 1.45, NOSE)]
    # The front face, a chamfered edge and the barrel to the panel seam at row 2.
    P += [(0.0, 2.4, NOSE), (0.38, 2.97, NOSE), (0.5, BODY_R, NOSE), (1.9, BODY_R, NOSE)]
    # Seam (a real gap), then the band (row 2) and its chamfer into the groove (row 3).
    P += [(1.97, 2.8, GROOVE), (2.07, 2.8, BAND), (2.14, BODY_R, BAND), (2.84, BODY_R, BAND),
          (3.08, 2.68, GROOVE), (3.95, 2.68, FFLANGE)]
    # Front collar (row 4): front face, chamfer, rim band, chamfer, back face down to the retainer.
    P += [(3.95, 3.5, FFLANGE), (4.38, FLANGE_R, FFLANGE), (4.62, FLANGE_R, FFLANGE), (5.0, 3.55, FFLANGE),
          (5.0, RIM_R + 0.15, RIM), (5.08, RIM_R, RIM), (5.66, RIM_R, CORE)]
    # Core cell between the retainers.
    P += core_profile()
    P += [(8.34, RIM_R, RIM2), (8.92, RIM_R, RIM2), (9.0, RIM_R + 0.15, RBODY)]
    # Rear body (row 9) and rear collar (row 10).
    P += [(9.0, 2.6, RBODY), (9.18, BODY_R, RBODY), (9.95, BODY_R, RFLANGE), (9.95, 3.55, RFLANGE),
          (10.38, FLANGE_R, RFLANGE), (10.62, FLANGE_R, RFLANGE), (11.0, 3.6, RFLANGE),
          (11.0, TAIL_R, SLOT)]
    # Tail core (under the plates), the cap (row 13) and the finned vent in its rear face.
    P += [(13.0, TAIL_R, CAP), (13.0, CAP_R, CAP), (13.62, CAP_R, CAP), (13.95, 1.72, CAP),
          (13.95, 1.25, BORE), (13.62, 1.25, BORE), (13.62, 0.58, CAP), (13.74, 0.52, CAP),
          (13.86, 0.32, CAP), (13.9, 0.0, CAP)]
    return P


def build_body(part):
    revolve(part, body_profile())
    # Tail plates over the dark core (rows 11-13): the centre spine (cols 5-6), the cheeks closing the
    # vent slots on row 12, the lower wall round the belly. Their gaps are the sprite's dark slots.
    L = circle_loop(TAIL_R)
    d = BODY_R - TAIL_R
    T.plate(part, L, 11.0, 12.96, SPINE, s0=-1.2, s1=1.2, d=d, c=0.12, depth=0.3, ystep=0.5, ch0=False)
    T.plate(part, L, 11.72, 12.96, WALL, s0=3.2, s1=5.6, d=d, c=0.12, depth=0.3, ystep=0.5)
    T.plate(part, L, 11.72, 12.96, WALL, s0=18.4, s1=20.8, d=d, c=0.12, depth=0.3, ystep=0.5)
    T.plate(part, L, 11.0, 12.96, WALL, s0=5.6, s1=18.4, d=d, c=0.12, depth=0.3, ystep=0.5, ch0=False)
    # Bolt rings on the collars' outer faces (front face of the front collar, back face of the rear).
    for k in range(8):
        a = 2 * math.pi * (k + 0.5) / 8
        r = 3.1
        bolt(part, (r * math.sin(a), 3.95, r * math.cos(a)), -1)
        r = 3.3
        bolt(part, (r * math.sin(a), 11.0, r * math.cos(a)), +1)
    # Fins across the tail vent (a cross), recessed in the cap's rear face.
    for k in range(4):
        a = 2 * math.pi * k / 4 + math.pi / 4
        ca, sa = math.cos(a), math.sin(a)
        pts = [(x * ca - z * sa, y, x * sa + z * ca) for x, y, z in cbox(0.5, 1.3, 13.6, 13.88, -0.09, 0.09, 0.03)]
        hull(part, pts, CAP)
    # Mount lugs low on both flanks of the barrel (below the waist, hidden from above): chamfered
    # blocks with a bolt, where the pod's mounting arm clamps.
    for side in (1, -1):
        a = math.radians(132)
        cx, cz = side * BODY_R * math.sin(a), BODY_R * math.cos(a)
        nx, nz = side * math.sin(a), math.cos(a)
        tx, tz = -nz * side, nx * side  # tangent
        pts = []
        for u in (-0.55, 0.55):
            for v, ch in ((-0.3, 0.0), (0.32, 0.12)):
                for y in (0.8 + ch, 1.7 - ch):
                    uu = u - math.copysign(ch, u)
                    pts.append((cx + tx * uu + nx * v, y, cz + tz * uu + nz * v))
        hull(part, pts, BOLT)


def build_sparks(part, frame):
    """Blue sparks crackling off the charged core: a glowing bead with four thin spikes, and a
    jagged arc back to the core for the ones that jumped clear of it."""
    seed = frame
    for row, col, idx in SPARKS[frame]:
        mat = {151: SP151, 154: SP154, 157: SP157}[idx]
        cx, cy = col - 6 + 0.5, row + 0.5
        pts = []
        for i in range(8):
            for j in range(1, 4):
                t, p = 2 * math.pi * i / 8, math.pi * j / 4
                pts.append((cx + 0.47 * math.sin(p) * math.cos(t), cy + 0.47 * math.sin(p) * math.sin(t), 0.47 * math.cos(p)))
        pts += [(cx, cy, 0.47), (cx, cy, -0.47)]
        hull(part, pts, mat)
        for k in range(4):
            t = math.pi / 4 + k * math.pi / 2 + 0.3 * math.sin(seed + k)
            dx, dy = math.cos(t), math.sin(t)
            tip = (cx + 0.95 * dx, cy + 0.95 * dy, 0.15 * math.sin(seed * 3 + k))
            base = [(cx + 0.3 * dx - 0.09 * dy, cy + 0.3 * dy + 0.09 * dx, 0.09),
                    (cx + 0.3 * dx + 0.09 * dy, cy + 0.3 * dy - 0.09 * dx, 0.09),
                    (cx + 0.3 * dx, cy + 0.3 * dy, -0.09)]
            hull(part, base + [tip], mat)
        side = 1 if cx > 0 else -1
        gap = abs(cx) - BODY_R
        if gap > 1.0:  # an arc back to the core's flank
            x0, x1 = cx - side * 0.35, side * 2.85
            ny = 4
            prev = None
            for s in range(ny + 1):
                u = s / ny
                jit = 0.0 if s in (0, ny) else 0.32 * math.sin(seed * 1.7 + s * 2.3 + row)
                p = (x0 + (x1 - x0) * u, cy + jit, 0.3 * math.sin(seed + s * 1.9) if 0 < s < ny else 0.0)
                if prev is not None:
                    tube = []
                    for q in (prev, p):
                        for k in range(4):
                            t = 2 * math.pi * k / 4
                            tube.append((q[0], q[1] + 0.065 * math.cos(t), q[2] + 0.065 * math.sin(t)))
                    hull(part, tube, ARC)
                prev = p


def finish(part, mats, coll, smooth_angle=None):
    """T.finish for a 12x14 sprite: X = x / 12, Y = (7 - y) / 12, Z = z / 12."""
    part.orient()
    bm = part.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    m = Matrix(((PX, 0, 0, 0), (0, -PX, 0, 7 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    me = bpy.data.meshes.new(part.name)
    bm.to_mesh(me)
    bm.free()
    for mat in mats:
        me.materials.append(mat)
    obj = bpy.data.objects.new(part.name, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(part.smooth_angle))
    return obj


# --- bake (copied from enemies/newshm-117.py: AO/roughness only, glowing parts left flat) ----------

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
    bpy.ops.uv.smart_project(angle_limit=math.radians(24), island_margin=0.006, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.004)
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
        ao_s.inputs["Distance"].default_value = 0.02
        ao_l = node("ShaderNodeAmbientOcclusion")
        ao_l.samples = 24
        ao_l.inputs["Distance"].default_value = 0.09
        bev = node("ShaderNodeBevel")
        bev.samples = 8
        bev.inputs["Radius"].default_value = 0.004
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
            nt.links.new(v, em.inputs["Color"])
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


# --- build -------------------------------------------------------------------------------------

def build(sprite, coll):
    mats = materials(sprite)
    P = Part(NAME, smooth_angle=32.0)
    build_body(P)
    body = finish(P, mats, coll)
    sparks = []
    for frame in SPARKS:
        S = Part(f"{NAME}-sparks-{frame}", smooth_angle=40.0)
        build_sparks(S, frame)
        s = finish(S, mats, coll)
        common.frame_part(s, [frame])
        sparks.append(s)
    return body, sparks, mats


def set_frame(objs, frame):
    """Show the model as on sprite frame `frame` (for renders): frame parts and frame colours."""
    for o in objs:
        if "tyrian_frames" in o:
            o.hide_render = frame not in list(o["tyrian_frames"])
    mats = {m for o in objs if o.type == "MESH" for m in o.data.materials if m}
    for m in mats:
        if "tyrian_base_rgb" not in m:
            bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
            mix = next((n for n in m.node_tree.nodes if n.type == "MIX" and n.blend_type == "MULTIPLY"), None)
            base = tuple(mix.inputs[7].default_value)[:3] if mix else tuple(bsdf.inputs["Base Color"].default_value)[:3]
            m["tyrian_base_rgb"] = list(base)
        rgb = m.get("tyrian_frame_rgb", {}).get(str(frame), m["tyrian_base_rgb"])
        rgb = tuple(rgb)
        bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        mix = next((n for n in m.node_tree.nodes if n.type == "MIX" and n.blend_type == "MULTIPLY"), None)
        if mix:
            mix.inputs[7].default_value = (*rgb, 1.0)
        else:
            bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
        if bsdf.inputs["Emission Strength"].default_value > 0:
            bsdf.inputs["Emission Color"].default_value = (*rgb, 1.0)
        m.diffuse_color = (*rgb, 1.0)


def camera(scene, name, location, look_at, ortho=None, lens=50, up="Y"):
    data = bpy.data.cameras.new(name)
    if ortho:
        data.type = "ORTHO"
        data.ortho_scale = ortho
    else:
        data.lens = lens
    cam = bpy.data.objects.new(name, data)
    scene.collection.objects.link(cam)
    cam.location = location
    direction = Vector(look_at) - Vector(location)
    cam.rotation_euler = direction.to_track_quat("-Z", up).to_euler()
    return cam


def set_engine(scene, want):
    try:
        scene.render.engine = want
    except TypeError as err:
        names = [e for e in str(err).replace("'", " ").replace(",", " ").replace("(", " ").replace(")", " ").split()
                 if e.isupper()]
        key = "WORKBENCH" if "WORKBENCH" in want else "EEVEE"
        scene.render.engine = next(e for e in names if key in e)


def render_tops(scene, objs, out):
    """Flat top views on the sprite grid (16 image px per sprite px), one per frame, for sprite_mask --measure."""
    set_engine(scene, "BLENDER_WORKBENCH")
    sh = scene.display.shading
    sh.light = "FLAT"
    sh.color_type = "MATERIAL"
    sh.show_cavity = False
    sh.show_object_outline = False
    scene.render.film_transparent = True
    scene.render.resolution_x, scene.render.resolution_y = 12 * 16, 14 * 16
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = "Standard"
    cam = camera(scene, "cc_top", (0, 0, 5), (0, 0, 0), ortho=14 / 12)
    cam.rotation_euler = (0, 0, 0)
    scene.camera = cam
    for f in ALL:
        set_frame(objs, f)
        scene.render.filepath = str(out / f"top_{f}.png")
        bpy.ops.render.render(write_still=True)


def render_views(scene, objs, out, frames=(258, 279, 298)):
    set_engine(scene, "BLENDER_EEVEE")
    scene.render.film_transparent = False
    try:
        scene.view_settings.view_transform = "Khronos PBR Neutral"
    except TypeError:
        scene.view_settings.view_transform = "Standard"
    if scene.world is None:
        scene.world = bpy.data.worlds.new("w")
    scene.world.use_nodes = True
    bg = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.09, 0.095, 0.11, 1)
    bg.inputs[1].default_value = 1.0
    for name in ("cc_sun", "cc_fill"):
        if bpy.data.objects.get(name):
            bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    sun = bpy.data.objects.new("cc_sun", bpy.data.lights.new("cc_sun", "SUN"))
    sun.data.energy = 4.5
    sun.rotation_euler = (Vector((0.45, -0.5, -1.0))).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(sun)
    fill = bpy.data.objects.new("cc_fill", bpy.data.lights.new("cc_fill", "SUN"))
    fill.data.energy = 1.3
    fill.rotation_euler = (Vector((-0.6, 0.6, -0.3))).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(fill)
    scene.render.resolution_x = scene.render.resolution_y = 420
    D = 3.0
    ext = 1.45
    t15, t32 = math.radians(15), math.radians(32)
    views = {
        "top": camera(scene, "v_top", (0, 0, D), (0, 0, 0), ortho=ext),
        "side": camera(scene, "v_side", (D, 0, 0), (0, 0, 0), ortho=ext, up="Z"),
        "front": camera(scene, "v_front", (0, D, 0), (0, 0, 0), ortho=ext * 0.75, up="Z"),
        "rear": camera(scene, "v_rear", (0, -D, 0), (0, 0, 0), ortho=ext * 0.75, up="Z"),
        "q34": camera(scene, "v_q34", (2.2, 2.0, 2.1), (0, 0, 0), lens=60, up="Z"),
        "q34r": camera(scene, "v_q34r", (-2.2, -2.2, 1.9), (0, 0, 0), lens=60, up="Z"),
        "game15": camera(scene, "v_game15", (0, -4.5 * math.sin(t15), 4.5 * math.cos(t15)), (0, 0, 0), lens=55),
        "game32": camera(scene, "v_game32", (0, -4.5 * math.sin(t32), 4.5 * math.cos(t32)), (0, 0, 0), lens=55),
        "under": camera(scene, "v_under", (0, 0, -D), (0, 0, 0), ortho=ext),
    }
    views["top"].rotation_euler = (0, 0, 0)
    views["under"].rotation_euler = (math.pi, 0, 0)
    for f in frames:
        set_frame(objs, f)
        for k, cam in views.items():
            if f != frames[0] and k not in ("top", "game15", "q34"):
                continue
            scene.camera = cam
            scene.render.filepath = str(out / f"view_{k}_{f}.png")
            bpy.ops.render.render(write_still=True)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out_dir = Path(argv[argv.index("--out") + 1]) if "--out" in argv else None
    bake = "--nobake" not in argv
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    scene = bpy.context.scene
    coll = common.reset_collection("charge_cannon")
    sprite = common.load_sprite(WT, REF)
    body, sparks, mats = build(sprite, coll)
    shell = common.outline_shell(body, coll, voxel=0.01, faces=800, smooth=6, inside=0.004)
    shell.name = f"{NAME}_outline"
    T.cull_hidden(body)
    if bake:
        # The shell and the sparks stay out of the bake's scene.
        for o in [shell] + sparks:
            o.hide_render = True
        bake_maps(body, tempfile.mkdtemp(prefix="cc_bake_"), "charge_cannon")
    objs = [body, shell] + sparks
    tris = {}
    for o in objs:
        o.data.calc_loop_triangles()
        tris[o.name] = len(o.data.loop_triangles)
    print("triangles", tris)
    common.export_sprite_model(WT, objs, "sidekicks/charge-cannon", sprite["sprites"],
                               image_format="WEBP" if bake else "AUTO")
    if out_dir:
        renders = out_dir / "renders"
        renders.mkdir(parents=True, exist_ok=True)
        shell.hide_render = True
        for o in sparks:
            o.hide_render = False
        render_tops(scene, [body] + sparks, renders)
        render_views(scene, [body] + sparks, renders)
        (renders / "stats.json").write_text(json.dumps({"triangles": tris}, indent=1))


main()
