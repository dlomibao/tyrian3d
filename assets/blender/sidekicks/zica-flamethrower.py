"""Zica Flamethrower (sidekick option 17, tyrian.shp#8 frames 87, 106, 125, 144), a 3D
version of its sprite to the player-ship hard-surface standard (DECISIONS D50-D53, D65, D74).

What it is: a small mounted side pod (style 0): a steel-blue flamethrower. A ringed nozzle barrel
out front feeds from a box housing (the pump / igniter block) flanked by two fuel tanks.

What the sprite shows (reference/models/sidekick-zica-flamethrower, 12x14, palette 5; the four
frames are pixel-identical, so one model serves them all; ink border only at 4 pixels, so the top
view covers the whole sprite):
- the nozzle: cols 4-7 (4 px), rows 1-6: light rows 1, 3, 5 are rings (muzzle ring 59, fins 58),
  dark rows 2, 4, 6 the slimmer core between them (54);
- row 5 cols 3/8 (52): short struts tying the barrel to the tanks; row 6 cols 3/8 open;
- the housing: cols 3-8, rows 7-13: a collar at row 7 (55), a deck of plates: a lit left rail
  (col 4, 59), a centre spine (cols 5-6, 59) broken by two dark-red sight glasses (rows 8 and 11,
  113/114), the right side (cols 7-8) in shadow (lighting, not paint: mirrored as rails);
- the fuel tanks: cols 0-2 / 9-11, rows 3-13, round (58), the nose raked inward to a point at row 3
  (inner edge straight, outer edge stepping out to row 5), the outer rear corner rounded (row 13).

Design: barrel = a revolve (chamfered muzzle ring with a dark bore and an igniter tip deep in it,
two chamfered cooling fins, a collar flange); housing = a chamfered block with modelled deck plates
(rails, spine segments, panel-line gaps) and recessed glowing sight glasses, hex bolts, a recessed
rear service panel; tanks = lofted round shells with pchip stations (raked nose, clamp straps with
brackets to the housing, a dark filler cap, a domed rear cap). Underside: closed, plain.

Run: tools/build-models.sh assets/blender/sidekicks/zica-flamethrower.py (or Blender directly with -- [--nobake] [--views DIR])
"""

import json
import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))
import common  # noqa: E402
import usp_talon as T  # noqa: E402
from usp_talon import Part, cbox, hull, pchip, frange  # noqa: E402

NAME = "zica-flamethrower"
REF = f"sidekick-{NAME}"
HERE = Path(__file__).resolve().parent
PX = 1 / 12
N = 24
ALL = [87, 106, 125, 144]

(MUZ, FIN, GROOVE, BORE, IGN, COLLAR, WALL, RAIL, SPINE, GLASS, BOLT, TANK, STRAP, CAP, STRUT,
 FILL) = range(16)

ZB = 0.95   # barrel axis height (px)
ZT = 0.35   # tank axis height
RT = 1.5    # tank radius (3 px)
HZ0, HZ1 = -1.25, 2.25  # housing block bottom / top


def materials(sprite):
    def steel(i, tag, rough=0.38, metal=0.35):
        return common.palette_material(sprite, i, f"zf_{tag}", metallic=metal, roughness=rough)
    # Palette index per part: median of the sprite pixels it covers, darkest/brightest left out.
    return [
        steel(59, "muzzle", 0.34),
        steel(58, "fin", 0.34),
        steel(54, "groove", 0.45),
        common.palette_material(sprite, 51, "zf_bore", metallic=0.1, roughness=0.8),
        common.palette_material(sprite, 114, "zf_igniter", metallic=0.0, roughness=0.3, emission_strength=0.9),
        steel(55, "collar"),
        steel(54, "wall", 0.45),
        steel(59, "rail", 0.34),
        steel(59, "spine", 0.32),
        common.palette_material(sprite, 114, "zf_glass", metallic=0.0, roughness=0.12, emission_strength=0.7),
        steel(56, "bolt", 0.3, 0.45),
        steel(58, "tank", 0.32, 0.4),
        steel(54, "strap", 0.42),
        steel(55, "cap", 0.4),
        steel(52, "strut", 0.45),
        steel(53, "filler", 0.4),
    ]


# --- geometry helpers (sprite px: x = column edge - 6, y = row edge, z up) -----------------------

def ring_pts(cx, y, cz, rx, rz, n=N):
    if rx <= 1e-6:
        return [(cx, y, cz)]
    return [(cx + rx * math.sin(2 * math.pi * i / n), y, cz + rz * math.cos(2 * math.pi * i / n)) for i in range(n)]


def tube(part, stations, n=N):
    """Rings [(y, cx, cz, rx, rz, mat)] along y joined into a closed tube (rx 0 = a pole)."""
    rings = [[part.v(p) for p in ring_pts(cx, y, cz, rx, rz, n)] for y, cx, cz, rx, rz, _ in stations]
    for k in range(len(stations) - 1):
        a, b = rings[k], rings[k + 1]
        y0, cx0, cz0, rx0, _, m = stations[k]
        y1, cx1, cz1, rx1, _, _ = stations[k + 1]
        for i in range(n):
            j = (i + 1) % n
            ang = 2 * math.pi * (i + 0.5) / n
            ny = -(rx1 - rx0)
            nr = (y1 - y0)
            out = (nr * math.sin(ang), ny, nr * math.cos(ang))
            if abs(nr) < 1e-9 and abs(ny) < 1e-9:
                out = (math.sin(ang), 0, math.cos(ang))
            if len(a) == 1:
                part.f((a[0], b[i], b[j]), m, out=out)
            elif len(b) == 1:
                part.f((a[i], a[j], b[0]), m, out=out)
            else:
                part.f((a[i], a[j], b[j], b[i]), m, out=out)
    if len(rings[0]) > 1:
        part.f(rings[0], stations[0][5], out=(0, -1, 0))
    if len(rings[-1]) > 1:
        part.f(rings[-1], stations[-1][5], out=(0, 1, 0))


def cyl_x(part, x0, x1, y, z, r, mat, n=10):
    pts = []
    for x in (x0, x1):
        for k in range(n):
            t = 2 * math.pi * k / n
            pts.append((x, y + r * math.cos(t), z + r * math.sin(t)))
    hull(part, pts, mat)


def cyl_z(part, x, y, z0, z1, r, mat, n=12, ch=0.06):
    pts = []
    for z, rr in ((z0, r), (z1 - ch, r), (z1, r - ch)):
        for k in range(n):
            t = 2 * math.pi * k / n
            pts.append((x + rr * math.cos(t), y + rr * math.sin(t), z))
    hull(part, pts, mat)


def hex_bolt(part, x, y, z, rad=0.16, h=0.12, mat=BOLT):
    pts = []
    for k in range(6):
        t = 2 * math.pi * k / 6 + math.pi / 6
        for dz, rr in ((-0.06, rad), (h * 0.65, rad), (h, rad * 0.72)):
            pts.append((x + rr * math.cos(t), y + rr * math.sin(t), z + dz))
    hull(part, pts, mat)


# --- the parts -----------------------------------------------------------------------------------

def build_barrel(part):
    """The nozzle: a revolve round the axis x 0, z ZB, front (row 1) to inside the housing (row 7.4)."""
    RF, RG = 1.97, 1.62   # ring / core radius (4 px / ~3.3 px wide)
    prof = [
        (2.0, 0.0, IGN), (1.85, 0.22, IGN), (1.75, 0.34, BORE),            # igniter tip deep in the bore
        (1.75, 0.95, BORE), (1.12, 0.95, MUZ), (1.0, 1.1, MUZ),            # bore wall, inner lip
        (1.0, 1.72, MUZ), (1.1, RF, MUZ), (1.84, RF, MUZ), (1.98, RG, GROOVE),   # muzzle ring (row 1)
        (2.9, RG, FIN), (3.04, RF, FIN), (3.86, RF, FIN), (4.0, RG, GROOVE),     # fin (row 3)
        (4.9, RG, FIN), (5.04, RF, FIN), (5.86, RF, FIN), (6.0, RG, GROOVE),     # fin (row 5)
        (6.55, RG, COLLAR), (6.55, 2.12, COLLAR), (6.68, 2.32, COLLAR),          # collar flange (row 7)
        (7.3, 2.32, COLLAR), (7.3, 1.2, COLLAR), (7.5, 0.0, COLLAR),
    ]
    tube(part, [(y, 0.0, ZB, r, r, m) for y, r, m in prof])
    # Bolt ring on the collar's front face.
    for k in range(6):
        a = 2 * math.pi * (k + 0.5) / 6
        r = 2.1
        x, z = r * math.sin(a), ZB + r * math.cos(a)
        if z < ZB - 0.5:
            continue
        pts = []
        for kk in range(6):
            t = 2 * math.pi * kk / 6
            for dy, rr in ((0.12, 0.13), (-0.04, 0.13), (-0.1, 0.09)):
                pts.append((x + rr * math.cos(t), 6.55 + dy, z + rr * math.sin(t)))
        hull(part, pts, BOLT)


def prism(part, poly, z0, z1, ch, mat):
    """A convex plan polygon [(x, y)] extruded z0..z1, its top edge chamfered by ch (inset to the centroid)."""
    cx = sum(p[0] for p in poly) / len(poly)
    cy = sum(p[1] for p in poly) / len(poly)
    pts = [(x, y, z0) for x, y in poly] + [(x, y, z1 - ch) for x, y in poly]
    for x, y in poly:
        dx, dy = cx - x, cy - y
        ln = math.hypot(dx, dy) or 1.0
        pts.append((x + dx / ln * ch * 1.2, y + dy / ln * ch * 1.2, z1))
    hull(part, pts, mat)


def mirror(poly):
    return [(-x, y) for x, y in reversed(poly)]


def build_housing(part):
    """The pump block, cols 3-8. Row 7 is the collar: the block's front corners are cut back there (the
    sprite's dark cols 3/8 on row 7); row 13 is its rear: a recessed rear face between two side cheeks
    and a centre coupling (the dark cols 4/7 on row 13 are the gaps)."""
    top = HZ1
    YR = 13.08  # recessed rear face
    plan = [(-1.95, 6.95), (1.95, 6.95), (3.0, 8.35), (3.0, YR), (-3.0, YR), (-3.0, 8.35)]
    prism(part, plan, HZ0, top, 0.3, WALL)
    # Bottom chamfer (a closed, plain underside).
    hull(part, cbox(-2.7, 2.7, 7.6, YR - 0.05, HZ0 - 0.22, HZ0 + 0.4, 0.22), WALL)
    # Rear cheeks: the side walls run on past the rear face to row 14 (cols 3 / 8).
    for sd in (-1, 1):
        x0, x1 = sorted((sd * 2.06, sd * 3.0))
        hull(part, cbox(x0, x1, YR - 0.3, 13.98, HZ0 + 0.1, top - 0.05, 0.16), WALL)
    # Centre coupling (cols 5-6, row 13): a round-shouldered fuel feed block with a dark port.
    hull(part, cbox(-0.98, 0.98, YR - 0.3, 13.82, HZ0 + 0.3, top - 0.1, 0.3), COLLAR)
    pts = []
    for k in range(12):
        t = 2 * math.pi * k / 12
        for y, rr in ((13.7, 0.62), (13.98, 0.55)):
            pts.append((rr * math.cos(t), y, 0.45 + rr * math.sin(t)))
    hull(part, pts, CAP)
    pts = [(0.34 * math.cos(2 * math.pi * k / 10), y, 0.45 + 0.34 * math.sin(2 * math.pi * k / 10))
           for k in range(10) for y in (13.9, 14.02)]
    hull(part, pts, BORE)
    # Deck plates: two rails and three spine segments, 0.1 px gaps between them (panel lines).
    rail = [(1.08, 7.22), (1.9, 7.22), (2.82, 8.45), (2.82, 12.95), (1.08, 12.95)]
    prism(part, rail, top - 0.3, top + 0.32, 0.16, RAIL)
    prism(part, mirror(rail), top - 0.3, top + 0.32, 0.16, RAIL)
    for y0, y1 in ((7.22, 7.92), (9.08, 10.92), (12.08, 13.72)):
        hull(part, cbox(-0.98, 0.98, y0, y1, top - 0.3, top + 0.45, 0.14), SPINE)
    # Sight glasses: recessed (below the plates), lit dark red, a slight dome.
    for y0 in (7.98, 10.98):
        pts = cbox(-0.92, 0.92, y0, y0 + 1.04, top - 0.3, top + 0.12, 0.26, 0.1)
        pts += [(x, y0 + 0.52, top + 0.2) for x in (-0.45, 0.45)]
        hull(part, pts, GLASS)
    # Hex bolts on the rails, front and rear.
    for sd in (-1, 1):
        for y in (8.4, 12.45):
            hex_bolt(part, sd * 1.95, y, top + 0.32)
    # Bolts on the cheeks' rear faces.
    for sd in (-1, 1):
        for z in (HZ0 + 0.7, top - 0.6):
            pts = []
            for kk in range(6):
                t = 2 * math.pi * kk / 6
                for dy, rr in ((-0.05, 0.12), (0.08, 0.12), (0.13, 0.08)):
                    pts.append((sd * 2.53 + rr * math.cos(t), 13.95 + dy, z + rr * math.sin(t)))
            hull(part, pts, BOLT)


def tank_stations(s):
    """The left (s=-1) or right tank: inner edge on the housing wall (|x| 3), raked nose, domed rear."""
    xi = 3.0
    # Outer edge |x| of the nose, from the tip at row 2.95 to full width at row 5.6 (the sprite's step).
    nose_y = [2.95, 3.4, 4.0, 4.6, 5.2, 5.7]
    nose_x = [3.2, 4.05, 4.85, 5.48, 5.88, 6.0]
    fo = pchip(nose_y, nose_x)
    st = []
    for y in frange(2.95, 5.7, 0.3):
        xo = fo(y)
        r = (xo - xi) / 2
        r = max(r, 0.14)
        st.append((y, s * (xi + r), ZT, r, RT * math.sqrt(r / RT), TANK))
    # A blunt rounded tip: a tiny cap ahead of the first ring.
    st.insert(0, (2.86, s * (xi + 0.1), ZT, 0.0, 0.0, TANK))
    cx = s * (xi + RT)
    # Clamp straps (rows 8 and 12): a raised band with chamfers.
    for y0 in (8.0, 11.7):
        st += [(y0, cx, ZT, RT, RT, STRAP), (y0 + 0.06, cx, ZT, RT + 0.12, RT + 0.12, STRAP),
               (y0 + 0.54, cx, ZT, RT + 0.12, RT + 0.12, STRAP), (y0 + 0.6, cx, ZT, RT, RT, TANK)]
    # Domed rear: the axis drifts inward so the outer rear corner rounds off (row 13 col 0 empty).
    rear_y = [12.9, 13.3, 13.6, 13.85, 14.0]
    rear_r = [RT, 1.38, 1.12, 0.75, 0.0]
    rear_c = [RT, RT - 0.08, RT - 0.3, RT - 0.55, RT - 0.75]
    for k, y in enumerate(rear_y):
        m = CAP if k >= 1 else TANK
        st.append((y, s * (xi + rear_c[k]), ZT, rear_r[k], rear_r[k], m))
    st.sort(key=lambda t: t[0])
    return st


def build_tanks(part):
    for s in (-1, 1):
        tube(part, tank_stations(s), n=18)
        cx = s * (3.0 + RT)
        # Strap brackets into the housing wall (seen from the side and the 3/4 views).
        for y0 in (8.0, 11.7):
            x0, x1 = sorted((s * 2.7, s * 3.35))
            hull(part, cbox(x0, x1, y0 + 0.05, y0 + 0.55, ZT + 0.8, ZT + 1.45, 0.08), STRAP)
        # Filler cap on top of the tank (col 1 row 10: the tank's darkest pixel).
        cyl_z(part, cx, 10.05, ZT + RT - 0.25, ZT + RT + 0.18, 0.42, FILL)
        cyl_z(part, cx, 10.05, ZT + RT + 0.1, ZT + RT + 0.26, 0.24, BOLT)
        # Strut from the barrel to the tank (row 5, col 3 / 8).
        x0, x1 = sorted((s * 1.55, s * 3.35))
        cyl_x(part, x0, x1, 5.45, ZB - 0.1, 0.42, STRUT)


def finish(part, mats, coll):
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


# --- bake (AO/roughness only, from charge-cannon_A / enemies/newshm-117.py) ------------------------

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
            continue
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


# --- renders -------------------------------------------------------------------------------------

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
    cam.rotation_euler = (Vector(look_at) - Vector(location)).to_track_quat("-Z", up).to_euler()
    return cam


def set_engine(scene, want):
    try:
        scene.render.engine = want
    except TypeError as err:
        names = [e for e in str(err).replace("'", " ").replace(",", " ").replace("(", " ").replace(")", " ").split()
                 if e.isupper()]
        key = "WORKBENCH" if "WORKBENCH" in want else "EEVEE"
        scene.render.engine = next(e for e in names if key in e)


def render_tops(scene, out):
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
    cam = camera(scene, "zf_top", (0, 0, 5), (0, 0, 0), ortho=14 / 12)
    cam.rotation_euler = (0, 0, 0)
    scene.camera = cam
    for f in ALL:
        scene.render.filepath = str(out / f"top_{f}.png")
        bpy.ops.render.render(write_still=True)


def render_views(scene, out):
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
    sun = bpy.data.objects.new("zf_sun", bpy.data.lights.new("zf_sun", "SUN"))
    sun.data.energy = 4.5
    sun.rotation_euler = Vector((0.45, -0.5, -1.0)).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(sun)
    fill = bpy.data.objects.new("zf_fill", bpy.data.lights.new("zf_fill", "SUN"))
    fill.data.energy = 1.3
    fill.rotation_euler = Vector((-0.6, 0.6, -0.3)).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(fill)
    scene.render.resolution_x = scene.render.resolution_y = 420
    D, ext = 3.0, 1.45
    t15, t32 = math.radians(15), math.radians(32)
    views = {
        "top": camera(scene, "v_top", (0, 0, D), (0, 0, 0), ortho=ext),
        "side": camera(scene, "v_side", (D, 0, 0), (0, 0, 0), ortho=ext, up="Z"),
        "front": camera(scene, "v_front", (0, D, 0), (0, 0, 0), ortho=ext * 0.85, up="Z"),
        "rear": camera(scene, "v_rear", (0, -D, 0), (0, 0, 0), ortho=ext * 0.85, up="Z"),
        "q34": camera(scene, "v_q34", (2.0, 2.0, 2.1), (0, 0, 0), lens=60, up="Z"),
        "q34r": camera(scene, "v_q34r", (-2.1, -2.1, 1.9), (0, 0, 0), lens=60, up="Z"),
        "game15": camera(scene, "v_game15", (0, -4.5 * math.sin(t15), 4.5 * math.cos(t15)), (0, 0, 0), lens=55),
        "game32": camera(scene, "v_game32", (0, -4.5 * math.sin(t32), 4.5 * math.cos(t32)), (0, 0, 0), lens=55),
        "under": camera(scene, "v_under", (0, 0, -D), (0, 0, 0), ortho=ext),
    }
    views["top"].rotation_euler = (0, 0, 0)
    views["under"].rotation_euler = (math.pi, 0, 0)
    for k, cam in views.items():
        scene.camera = cam
        scene.render.filepath = str(out / f"view_{k}.png")
        bpy.ops.render.render(write_still=True)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    bake = "--nobake" not in argv
    views = Path(argv[argv.index("--views") + 1]) if "--views" in argv else None
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    scene = bpy.context.scene
    coll = common.reset_collection("zica_flamethrower")
    sprite = common.load_sprite(WT, REF)
    mats = materials(sprite)
    P = Part(NAME, smooth_angle=34.0)
    build_barrel(P)
    build_housing(P)
    build_tanks(P)
    body = finish(P, mats, coll)
    shell = common.outline_shell(body, coll, voxel=0.01, faces=900, smooth=6, inside=0.004)
    shell.name = f"{NAME}_outline"
    T.cull_hidden(body)
    if bake:
        shell.hide_render = True
        bake_maps(body, tempfile.mkdtemp(prefix="zf_bake_"), "zica_flamethrower")
    objs = [body, shell]
    tris = {}
    for o in objs:
        o.data.calc_loop_triangles()
        tris[o.name] = len(o.data.loop_triangles)
    print("triangles", tris)
    common.export_sprite_model(WT, objs, "sidekicks/zica-flamethrower", sprite["sprites"],
                               image_format="WEBP" if bake else "AUTO")
    if views:
        views.mkdir(parents=True, exist_ok=True)
        shell.hide_render = True
        render_tops(scene, views)
        render_views(scene, views)
        (views / "stats.json").write_text(json.dumps({"triangles": tris}, indent=1))


main()
