"""Plasma Storm (sidekick option 9, tyrian.shp#8 frames 224, 243, 262, 281, 300), a 3D
version of its sprite to the player-ship hard-surface standard (DECISIONS D50-D53, D65, D74).

What it is: a small mounted side pod (style 0), a plasma cannon: a ribbed green plasma containment
canister lying nose-forward, plugged into a wide grey power housing with two exhaust nozzles out
of its back. Its shots are separate flat art (D31a); the five frames only pulse the greens.

What the sprite shows (reference/models/sidekick-plasma-storm, 12x14 block, the pod's axis on the
column edge 5.5; inner mask = what the top view covers, its ink border left to the game's outline):
- row 1 (3 px): the emitter lens, the brightest green (207 -> 203), its rim 202 -> 197;
- rows 2, 4, 6 (5 px): dark-green containment rings (193; 194/195 is their sheen);
- rows 3, 5, 7: the glowing plasma between them (196..207, pulsing by frame);
- rows 5-6 cols 4-6: a grey clamp block on top (10/11/13: satin metal, its 13s are sheen), row 7
  col 5 its grey rib back to the collar, the 193 beside it the clamp's dark-green saddle;
- row 8 (7 px): the grey collar the canister plugs into, two green indicator lights on top
  (cols 4 and 6, 197 -> 201);
- rows 9-10 (9 px): the housing's front flange (row 9, lit 12) and a dark cooling groove across
  its top (row 10, 4), the grey cheeks at cols 1 and 9 bridging it;
- row 11 (7 px): the rear housing (8); row 12: two exhaust nozzles (cols 3-4, 6-7; 5/3), an ink
  gap between them.

Design: lofts in sprite px (x = column - 5.5 from the axis, y = row edge, z up, the canister axis at
z 0), each section a superellipse so round parts stay round (the canister, collar, nozzles) and the
housing is a chamfered rounded box; plan widths are pchip curves through the middles of the inner
mask's steps. Machined detail where the cameras see: chamfered proud rings with the plasma recessed
between them, a lens set in a cowl lip, a chamfered clamp with a saddle and rib, inset indicator
lights, a bolt ring on the flange's front face, vent fins across the groove, side cheek rails with
a mount socket on each flank (where the pod clamps to the ship), panel seams, flared nozzles with
dark bores. Underside: the same closed lofts, nothing more.

Run: tools/build-models.sh -j 2 assets/blender/sidekicks/plasma-storm.py
(or Blender --background --python this -- [--nobake] [--out DIR] for review renders in DIR/renders).
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
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import usp_talon as T  # noqa: E402
from usp_talon import Part, cbox, hull, pchip, frange  # noqa: E402

NAME = "plasma-storm"
REF = f"sidekick-{NAME}"
HERE = Path(__file__).resolve().parent
PX = 1 / 12
AXIS = 5.5 - 6.0  # the pod's axis in block px (the 12x14 block is centred on the origin)
ALL = [224, 243, 262, 281, 300]

(LENS, LENS_RIM, COWL, RING, BAND3, BAND5, BAND7, CLAMP, RIB, COLLAR, LIGHT, FLANGE, GROOVE, FIN,
 CHEEK, REAR, NOZZLE, BORE, BOLT, SOCKET, ROD) = range(21)


def materials(sprite):
    """Palette index per part: the median of the sprite pixels it covers, the ink, the darkest shading
    and the brightest highlights left out; frames= where the plasma pulse changes it."""
    def metal(i, tag, rough=0.42, met=0.38, frames=None):
        return common.palette_material(sprite, i, f"ps_{tag}", metallic=met, roughness=rough, frames=frames)

    def glow(i, tag, e, frames=None):
        return common.palette_material(sprite, i, f"ps_{tag}", metallic=0.0, roughness=0.3,
                                       emission_strength=e, frames=frames)
    return [
        glow(202, "lens", 1.0, {262: 197, 281: 197, 300: 197}),
        glow(197, "lensrim", 0.8, {262: 196, 281: 196, 300: 196}),
        metal(193, "cowl", rough=0.38, met=0.4),
        metal(193, "ring", rough=0.38, met=0.4),
        glow(197, "band3", 0.9, {243: 201, 262: 203, 281: 199, 300: 199}),
        glow(196, "band5", 0.9, {262: 201, 281: 201, 300: 197}),
        glow(196, "band7", 0.9, {262: 197, 281: 201, 300: 201}),
        metal(11, "clamp", rough=0.38),
        metal(10, "rib"),
        metal(13, "collar", rough=0.4),
        glow(197, "light", 1.0, {262: 198, 281: 201, 300: 201}),
        metal(12, "flange", rough=0.4),
        metal(4, "groove", rough=0.6, met=0.2),
        metal(5, "fin", rough=0.5, met=0.3),
        metal(10, "cheek"),
        metal(8, "rear"),
        metal(5, "nozzle", rough=0.45),
        common.palette_material(sprite, 1, "ps_bore", metallic=0.1, roughness=0.8),
        metal(10, "bolt", rough=0.32, met=0.45),
        metal(3, "socket", rough=0.5, met=0.3),
        metal(8, "rod", rough=0.35, met=0.45),
    ]


# --- geometry helpers (sprite px) ---------------------------------------------------------------

def sect(w, h, zc=0.0, e=2.0, n=24, xc=0.0):
    """A superellipse section (x, z): half width w, half height h, exponent e (2 round, higher
    squarer), starting at the top and running clockwise seen from the front."""
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        s, c = math.sin(t), math.cos(t)
        x = w * math.copysign(abs(s) ** (2 / e), s)
        z = h * math.copysign(abs(c) ** (2 / e), c)
        pts.append((xc + x, zc + z))
    return pts


def loft(part, secs, n=24, xc=0.0, cap0=True, cap1=True):
    """A tube along y through sections [(y, w, h, zc, e, mat)] (mat colours the band to the next
    section). Faces are oriented by the profile's outward normal, so steps, recesses and bores face
    the right way. A section with w == 0 is a point (a closed tip)."""
    rings = []
    for y, w, h, zc, e, _ in secs:
        if w <= 1e-6:
            rings.append([part.v((xc, y, zc))])
        else:
            rings.append([part.v((x, y, z)) for x, z in sect(w, h, zc, e, n, xc)])
    for k in range(len(secs) - 1):
        y0, w0, h0, z0, _, m = secs[k]
        y1, w1, h1, z1 = secs[k + 1][:4]
        r0, r1 = 0.5 * (w0 + h0), 0.5 * (w1 + h1)
        ny, nr = -(r1 - r0), (y1 - y0)
        a, b = rings[k], rings[k + 1]
        for i in range(n):
            j = (i + 1) % n
            t = 2 * math.pi * (i + 0.5) / n
            out = (nr * math.sin(t), ny, nr * math.cos(t))
            if len(a) == 1:
                part.f((a[0], b[i], b[j]), m, out=out)
            elif len(b) == 1:
                part.f((a[i], a[j], b[0]), m, out=out)
            else:
                part.f((a[i], a[j], b[j], b[i]), m, out=out)
    if cap0 and len(rings[0]) > 1:
        part.f(rings[0], secs[0][5], out=(0, -1, 0))
    if cap1 and len(rings[-1]) > 1:
        part.f(rings[-1], secs[-2][5], out=(0, 1, 0))


def bolt(part, centre, normal, rad=0.2, h=0.14, mat=BOLT):
    """A hex bolt head standing h along `normal` (a unit axis vector) from centre."""
    nv = Vector(normal).normalized()
    a = nv.orthogonal().normalized()
    b = nv.cross(a)
    c = Vector(centre)
    pts = []
    for k in range(6):
        t = 2 * math.pi * k / 6
        d = a * math.cos(t) + b * math.sin(t)
        for dh, rr in ((-0.06, rad), (h * 0.65, rad), (h, rad * 0.72)):
            pts.append(tuple(c + nv * dh + d * rr))
    hull(part, pts, mat)


def rod(part, p0, p1, r, mat, n=8):
    """A straight round rod from p0 to p1 (a convex hull of two octagons)."""
    p0, p1 = Vector(p0), Vector(p1)
    ax = (p1 - p0).normalized()
    a = ax.orthogonal().normalized()
    b = ax.cross(a)
    pts = []
    for p in (p0, p1):
        for k in range(n):
            t = 2 * math.pi * k / n
            pts.append(tuple(p + (a * math.cos(t) + b * math.sin(t)) * r))
    hull(part, pts, mat)


# --- the pod ------------------------------------------------------------------------------------

RR = 2.5    # the rings' radius: the inner mask's 5 px (rows 2-7)
RP = 2.18   # the plasma's radius between the rings
CH = 0.16   # chamfer on the rings
COL_W, COL_H = 3.45, 3.05   # the collar (row 8: 7 px)
FL_W, FL_H, FL_Z = 4.45, 2.95, 0.15   # the housing's front flange (rows 9-10: 9 px)
RE_W, RE_H, RE_Z = 3.45, 2.6, 0.05    # the rear housing (row 11: 7 px)
BOX = 4.0   # the housing's superellipse exponent (a rounded box)


def build_canister(part):
    # The emitter lens (row 1): a glowing dome standing out of a thin bezel, then the cowl flaring
    # into the first ring (row 2).
    dome = [(0.62 + 1.25 * (1 - math.cos(a)), 1.42 * math.sin(a))
            for a in [math.radians(d) for d in (0, 12, 25, 38, 52, 66, 80, 90)]]
    loft(part, [(y, w, w, 0, 2, LENS) for y, w in dome] + [
        (1.88, 1.42, 1.42, 0, 2, LENS_RIM), (1.88, 1.58, 1.58, 0, 2, LENS_RIM), (1.97, 1.62, 1.62, 0, 2, LENS_RIM),
        (1.97, 1.72, 1.72, 0, 2, COWL), (2.06, 2.25, 2.25, 0, 2, COWL), (2.16, RR - 0.04, RR - 0.04, 0, 2, COWL),
        (2.24, RR, RR, 0, 2, RING), (2.9 - CH, RR, RR, 0, 2, RING), (2.9, RR - CH, RR - CH, 0, 2, RING),
        (2.9, RP, RP, 0, 2, BAND3),
        # plasma (row 3), ring (row 4), plasma (row 5), ring (row 6), plasma (row 7)
        (4.08, RP, RP, 0, 2, RING), (4.08, RR - CH, RR - CH, 0, 2, RING), (4.08 + CH, RR, RR, 0, 2, RING),
        (4.92 - CH, RR, RR, 0, 2, RING), (4.92, RR - CH, RR - CH, 0, 2, RING), (4.92, RP, RP, 0, 2, BAND5),
        (6.08, RP, RP, 0, 2, RING), (6.08, RR - CH, RR - CH, 0, 2, RING), (6.08 + CH, RR, RR, 0, 2, RING),
        (6.92 - CH, RR, RR, 0, 2, RING), (6.92, RR - CH, RR - CH, 0, 2, RING), (6.92, RP, RP, 0, 2, BAND7),
        # the root ring entering the collar
        (7.72, RP, RP, 0, 2, RING), (7.72, RR - CH, RR - CH, 0, 2, RING), (7.72 + CH, RR, RR, 0, 2, RING),
        (8.3, RR, RR, 0, 2, RING),
    ], n=24)
    # Two tie-rods along the lower flanks, through the rings (seen from the side, under the waist).
    for side in (1, -1):
        t = math.radians(122)
        r = RR - 0.08
        x, z = side * r * math.sin(t), r * math.cos(t)
        rod(part, (x, 1.7, z), (x, 8.2, z), 0.2, ROD)
    # The clamp on top (rows 5-6, cols 4-6): a chamfered block on the rings, its saddle (row 7) and
    # its rib back to the collar (col 5).
    hull(part, cbox(-1.42, 1.42, 4.98, 6.98, 1.75, 2.95, 0.2, 0.18), CLAMP)
    hull(part, cbox(-1.42, 1.42, 6.98, 7.9, 1.9, 2.7, 0.12, 0.12), COWL)
    hull(part, cbox(-0.48, 0.48, 6.9, 8.3, 2.0, 2.98, 0.14, 0.16), RIB)
    # Two bolts on the clamp's front face.
    for x in (-0.75, 0.75):
        bolt(part, (x, 4.98, 2.4), (0, -1, 0), rad=0.17, h=0.1)


def build_housing(part):
    # The collar (row 8): a round ring the canister plugs into, chamfered front and back.
    loft(part, [
        (7.95, RR + 0.05, RR + 0.05, 0, 2, COLLAR), (7.95, COL_W - 0.35, COL_H - 0.3, 0, 2, COLLAR),
        (8.12, COL_W - 0.05, COL_H, 0, 2, COLLAR), (8.25, COL_W, COL_H, 0, 2.2, COLLAR),
        (8.85, COL_W, COL_H, 0, 2.2, COLLAR), (9.1, COL_W - 0.2, COL_H - 0.2, 0, 2.2, COLLAR),
    ], n=32)
    # Its two indicator lights on top (cols 4 and 6): glowing lenses in chamfered bezels.
    for side in (1, -1):
        x0, x1 = sorted((side * 0.6, side * 1.4))
        hull(part, cbox(x0, x1, 8.18, 8.86, 2.3, 3.08, 0.12, 0.1), LIGHT)
    # The flange (row 9): a chamfered shoulder out of the collar, a lit top, a seam, then into the
    # groove (row 10) and the side cheeks; the rear housing (row 11) closes to its back face.
    fw = pchip([8.75, 9.0, 9.25, 9.6, 10.05], [COL_W - 0.3, 3.9, FL_W - 0.12, FL_W, FL_W])
    loft(part, [
        (8.8, COL_W - 0.35, 2.6, FL_Z, BOX, FLANGE),
        (8.8, fw(8.8) + 0.1, 2.55, FL_Z, BOX, FLANGE),
        (9.0, fw(9.0), FL_H - 0.25, FL_Z, BOX, FLANGE),
        (9.25, fw(9.25), FL_H - 0.05, FL_Z, BOX, FLANGE),
        (9.45, fw(9.45), FL_H, FL_Z, BOX, FLANGE),
        (9.95, FL_W, FL_H, FL_Z, BOX, FLANGE),
        (10.1, FL_W - 0.12, FL_H - 0.14, FL_Z, BOX, FLANGE),
        (10.1, FL_W - 0.12, FL_H - 0.62, FL_Z, BOX, FLANGE),
    ], n=32, cap1=True)
    # The groove core (row 10): the dark recessed neck between flange and rear block.
    loft(part, [(10.05, 3.95, 2.35, FL_Z, BOX, GROOVE), (11.0, 3.95, 2.35, FL_Z, BOX, GROOVE)], n=32)
    # Vent fins across the groove (cols 2-8), standing up to just under the flange top.
    for x in frange(-2.5, 2.5, 1.0):
        hull(part, cbox(x - 0.09, x + 0.09, 10.12, 10.95, 0.5, 2.62, 0.03, 0.05), FIN)
    # The rear housing (row 11): front chamfer, a body, a seam, and the back face (row 12 edge).
    loft(part, [
        (10.92, RE_W - 0.3, RE_H - 0.3, RE_Z, BOX, REAR),
        (11.05, RE_W, RE_H, RE_Z, BOX, REAR), (11.4, RE_W, RE_H, RE_Z, BOX, REAR),
        (11.42, RE_W - 0.07, RE_H - 0.07, RE_Z, BOX, REAR), (11.5, RE_W - 0.07, RE_H - 0.07, RE_Z, BOX, REAR),
        (11.52, RE_W, RE_H, RE_Z, BOX, REAR), (11.82, RE_W, RE_H, RE_Z, BOX, REAR),
        (12.0, RE_W - 0.22, RE_H - 0.22, RE_Z, BOX, REAR),
    ], n=32)
    # The cheeks (cols 1 and 9, rows 9.6-11): rails along the flanks tying the flange to the rear
    # block across the groove, each with the mount socket where the pod clamps to the ship.
    for side in (1, -1):
        x0, x1 = (3.55, FL_W - 0.02) if side > 0 else (-FL_W + 0.02, -3.55)
        hull(part, cbox(x0, x1, 9.7, 11.15, -1.6, 2.05, 0.14, 0.14), CHEEK)
        xs = side * (FL_W - 0.02)
        # The socket: a short boss along x on the rail's outer face, a bolt in it.
        cx, cy, cz = xs, 10.42, 0.2
        pts_o, pts_i = [], []
        for k in range(12):
            t = 2 * math.pi * k / 12
            pts_o.append((cx, cy + 0.55 * math.cos(t), cz + 0.55 * math.sin(t)))
            pts_o.append((cx + side * 0.06, cy + 0.5 * math.cos(t), cz + 0.5 * math.sin(t)))
        hull(part, pts_o, SOCKET)
        bolt(part, (cx + side * 0.06, cy, cz), (side, 0, 0), rad=0.26, h=0.04)
    # A bolt ring on the flange's front face (the shoulder round the collar), seen from the front.
    for k in range(10):
        t = 2 * math.pi * (k + 0.5) / 10
        x, z = 3.95 * math.sin(t), FL_Z + 2.45 * math.cos(t)
        if abs(x) < 3.0 and z > 0:
            continue  # the top is the lit shoulder; the bolts go round the sides and below
        bolt(part, (x * 0.98, 8.92, z * 0.98), (0, -1, 0), rad=0.17, h=0.1)
    # A bolted thrust plate on the back face (the tilted game camera looks at it from behind).
    hull(part, cbox(-2.75, 2.75, 11.9, 12.1, -1.75, 1.95, 0.08, 0.1), NOZZLE)
    for x in (-2.35, 2.35):
        for z in (-1.35, 1.55):
            bolt(part, (x, 12.1, z), (0, 1, 0), rad=0.17, h=0.08)
    hull(part, cbox(-0.25, 0.25, 12.06, 12.18, -1.2, 1.4, 0.05), REAR)  # a stiffener rib between the nozzles
    # The two exhaust nozzles out of the back face (cols 3-4, 6-7): flared bells, dark bores.
    for side in (1, -1):
        loft(part, [
            (11.7, 0.82, 0.82, 0.25, 2, NOZZLE), (12.15, 0.82, 0.82, 0.25, 2, NOZZLE),
            (12.55, 0.9, 0.9, 0.25, 2, NOZZLE), (12.82, 0.98, 0.98, 0.25, 2, NOZZLE),
            (12.88, 0.98, 0.98, 0.25, 2, NOZZLE), (12.88, 0.78, 0.78, 0.25, 2, BORE),
            (12.4, 0.62, 0.62, 0.25, 2, BORE), (12.38, 0.0, 0.0, 0.25, 2, BORE),
        ], n=16, xc=side * 1.5)


def finish(part, mats, coll):
    """Sprite px -> Blender: X = (x + AXIS) / 12, Y = (7 - y) / 12, Z = z / 12."""
    part.orient()
    bm = part.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    m = Matrix(((PX, 0, 0, AXIS * PX), (0, -PX, 0, 7 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
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


# --- bake (copied from enemies/newshm-117.py via charge-cannon A: AO/roughness only) ------------

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


# --- build and review renders ------------------------------------------------------------------

def build(sprite, coll):
    mats = materials(sprite)
    P = Part(NAME, smooth_angle=32.0)
    build_canister(P)
    build_housing(P)
    return finish(P, mats, coll), mats


def set_frame(objs, frame):
    """Show the model as on sprite frame `frame` (for renders): the frame colours."""
    mats = {m for o in objs if o.type == "MESH" for m in o.data.materials if m}
    for m in mats:
        bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        mix = next((n for n in m.node_tree.nodes if n.type == "MIX" and n.blend_type == "MULTIPLY"), None)
        if "tyrian_base_rgb" not in m:
            base = tuple(mix.inputs[7].default_value)[:3] if mix else tuple(bsdf.inputs["Base Color"].default_value)[:3]
            m["tyrian_base_rgb"] = list(base)
        rgb = tuple(m.get("tyrian_frame_rgb", {}).get(str(frame), m["tyrian_base_rgb"]))
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
    """Flat top views on the sprite grid (16 image px per sprite px), per frame, for sprite_mask --measure."""
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
    cam = camera(scene, "ps_top", (0, 0, 5), (0, 0, 0), ortho=14 / 12)
    cam.rotation_euler = (0, 0, 0)
    scene.camera = cam
    for f in ALL:
        set_frame(objs, f)
        scene.render.filepath = str(out / f"top_{f}.png")
        bpy.ops.render.render(write_still=True)


def render_views(scene, objs, out, frames=(224, 262, 300)):
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
    sun = bpy.data.objects.new("ps_sun", bpy.data.lights.new("ps_sun", "SUN"))
    sun.data.energy = 4.5
    sun.rotation_euler = (Vector((0.45, -0.5, -1.0))).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(sun)
    fill = bpy.data.objects.new("ps_fill", bpy.data.lights.new("ps_fill", "SUN"))
    fill.data.energy = 1.3
    fill.rotation_euler = (Vector((-0.6, 0.6, -0.3))).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(fill)
    scene.render.resolution_x = scene.render.resolution_y = 420
    D = 3.0
    ext = 1.4
    t15, t32 = math.radians(15), math.radians(32)
    views = {
        "top": camera(scene, "v_top", (0, 0, D), (0, 0, 0), ortho=ext),
        "side": camera(scene, "v_side", (D, 0, 0), (0, 0, 0), ortho=ext),
        "front": camera(scene, "v_front", (0, D, 0), (0, 0, 0), ortho=ext * 0.75),
        "rear": camera(scene, "v_rear", (0, -D, 0), (0, 0, 0), ortho=ext * 0.75),
        "q34": camera(scene, "v_q34", (2.2, 2.0, 2.1), (0, 0, 0), lens=60),
        "q34r": camera(scene, "v_q34r", (-2.2, -2.2, 1.9), (0, 0, 0), lens=60),
        "game15": camera(scene, "v_game15", (0, -4.5 * math.sin(t15), 4.5 * math.cos(t15)), (0, 0, 0), lens=55),
        "game32": camera(scene, "v_game32", (0, -4.5 * math.sin(t32), 4.5 * math.cos(t32)), (0, 0, 0), lens=55),
        "under": camera(scene, "v_under", (0, 0, -D), (0, 0, 0), ortho=ext),
    }
    views["top"].rotation_euler = (0, 0, 0)
    h = math.pi / 2
    views["side"].rotation_euler = (h, 0, h)
    views["front"].rotation_euler = (h, 0, math.pi)
    views["rear"].rotation_euler = (h, 0, 0)
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
    coll = common.reset_collection("plasma_storm_A")
    sprite = common.load_sprite(WT, REF)
    body, mats = build(sprite, coll)
    shell = common.outline_shell(body, coll, voxel=0.01, faces=800, smooth=6, inside=0.004)
    shell.name = f"{NAME}_outline"
    T.cull_hidden(body)
    if bake:
        shell.hide_render = True
        bake_maps(body, tempfile.mkdtemp(prefix="ps_bake_"), "plasma_storm")
    objs = [body, shell]
    tris = {}
    for o in objs:
        o.data.calc_loop_triangles()
        tris[o.name] = len(o.data.loop_triangles)
    print("triangles", tris)
    common.export_sprite_model(WT, objs, "sidekicks/plasma-storm", sprite["sprites"],
                               image_format="WEBP" if bake else "AUTO")
    if out_dir:
        renders = out_dir / "renders"
        renders.mkdir(parents=True, exist_ok=True)
        shell.hide_render = True
        render_tops(scene, [body], renders)
        render_views(scene, [body], renders)
        (renders / "stats.json").write_text(json.dumps({"triangles": tris}, indent=1))


main()
