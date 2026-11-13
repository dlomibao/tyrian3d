"""Blue-steel hover pod (newsh0.shp frames 229, 231, 233), a hard-surface pod that is its sprite in
3D. Sibling of batch 2's newsh0-125 armoured hover pod and batch 3's newsh0-153 cross pod (same
build, style, scale and height).

What it is: a small flyer of BOTANY B (2.11, ground layer scroll 1): its spawns swoop on right-angle
2 px/tick patrols (ev19 links), often in pairs at dx +-24, so it hovers: a round closed belly,
centred near z = 0, not a ground crawler. Front is DOWN the screen (the vent and the lights face
the player). Symmetric about the column edge 12 (cols 11 | 12).

Read from the sprite (inner mask 14 x 16 px, rows 8-23, cols 5-18):
  - an armoured carapace (rows 8-14, widening from cols 7-16 at row 9 to cols 5-18 at row 11), its
    top notched at the front (cols 11-12, rows 7-8);
  - two bright ribs (cols 9-10 / 13-14) running back from rounded humps at the notch (row 8, cols
    8-10 / 13-15) to row 14, a dark channel between them (cols 11-12, rows 9-13: 50-53);
  - a dark seam across the carapace's back edge (row 14: 52-54);
  - three prongs behind it, split by dark slots (cols 9 / 14, rows 15-22): two hover nacelles
    (cols 5-8 / 15-18, rows 15-23, their crests col 7 / 16 bright) and a central snout (cols
    10-13, rows 14-22, its spine cols 11-12 bright) with a red-hot vent across it (rows 18-20:
    115 rim, 116/119 core, 121 heart) that is the same on every frame;
  - on each nacelle a slanting row of three lights (cols 8/7/6, rows 20/21/22). The frames only
    charge them: 113/114/116 (229), 115/116/118 (231), 117/121/120 (233). Lights are frame parts.

Palette index per region (sprite median, darkest shading and brightest sheen ignored): checked
by --measure. Texture: AO/roughness bake only (no foil), outline shell from a sealed copy (D51/D90).

Run: blender --background --factory-startup --python newsh0-229.py -- [--no-bake] [--out X.glb]
                                                                    [--measure m.json] [--render DIR]
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))
sys.path.insert(0, str(WT / "tools"))
import common  # noqa: E402

NAME = "newsh0-229"
FRAMES = (229, 231, 233)
PX = 1 / 12
AXU = 12.0   # axis of symmetry: the edge between columns 11 and 12
CY = 15.9    # the pod's middle row edge (renders look here)

(SHELL, RIB, CHANNEL, SEAM, LEG, SNOUT, CHASSIS, HOUSING, BOLT,
 VENT, VCORE, VHEART,
 L113, L114, L115, L116, L117, L118, L120, L121) = range(20)
MATS = {
    SHELL: (55, 0.3, 0.36, 0.0),     # carapace flanks (cols 5-8 / 15-18, rows 10-13: 54-58; one step
                                     # under their median so the ribs stand out in game as in the sprite)
    RIB: (59, 0.3, 0.3, 0.0),        # the ribs (cols 9-10 / 13-14: 58-62, the top sheen)
    CHANNEL: (52, 0.4, 0.45, 0.0),   # channel between the ribs (cols 11-12, rows 9-13: 50-53)
    SEAM: (53, 0.4, 0.45, 0.0),      # the seam band at row 14 (52-54)
    LEG: (55, 0.3, 0.36, 0.0),       # nacelles (53-58, crest 59-61 is sheen)
    SNOUT: (57, 0.3, 0.34, 0.0),     # snout (55-61)
    CHASSIS: (50, 0.45, 0.5, 0.0),   # belly keel showing in the slots (48 ink; underside plain)
    HOUSING: (51, 0.45, 0.45, 0.0),  # the light rails on the nacelles
    BOLT: (54, 0.45, 0.4, 0.0),      # bolts
    # glows (D126: strength 1 = the palette colour unlit; D173: glow surfaces metallic 1, rough)
    VENT: (115, 1.0, 0.85, 1.0),     # the vent's rim (rows 18-19)
    VCORE: (119, 1.0, 0.85, 1.0),    # its core (116 / 119, row 20)
    VHEART: (121, 1.0, 0.85, 1.0),   # its orange heart (row 19)
    L113: (113, 1.0, 0.85, 1.0),     # nacelle lights, by frame (see LIGHTS)
    L114: (114, 1.0, 0.85, 1.0),
    L115: (115, 1.0, 0.85, 1.0),
    L116: (116, 1.0, 0.85, 1.0),
    L117: (117, 1.0, 0.85, 1.0),
    L118: (118, 1.0, 0.85, 1.0),
    L120: (120, 1.0, 0.85, 1.0),
    L121: (121, 1.0, 0.85, 1.0),
}
GLOW = tuple(range(9, 20))
# Light steel, as newsh0-125 fix round 1 and newsh0-153: metallic 0.3 keeps the palette blue's
# value, the F0 of IOR 2.0 through Specular IOR Level (D176) gives the crowns a white sheen like the
# sprite's 60-62.
STEEL = (SHELL, RIB, LEG, SNOUT)
STEEL_SPEC = 0.5 * ((1.0 / 3.0) ** 2 / 0.04)
TINT = (0.97, 0.985, 1.0)

# --- geometry helpers (sprite px: x from the axis, y = sprite row edge, down the screen, z up) ----

# --- geometry helpers (sprite px: xr from the axis, y = sprite row edge, down the screen, z up) ----

class Mesh:
    def __init__(self):
        self.bm = bmesh.new()

    def face(self, vs, mat):
        try:
            f = self.bm.faces.new(vs)
        except ValueError:
            return None
        f.material_index = mat
        return f


def ring(cx, y, hw, zb, zt, n=20, p=2.6, pb=None, hwb=None):
    """A superellipse section (x-z) at row y: half width hw (hwb at the bottom), from zb to zt."""
    pb = p if pb is None else pb
    hwb = hw if hwb is None else hwb
    zc, hh = (zb + zt) / 2, (zt - zb) / 2
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        c, s = math.cos(t), math.sin(t)
        e = p if s >= 0 else pb
        w = hw if s >= 0 else hwb
        x = cx + w * math.copysign(abs(c) ** (2 / e), c)
        z = zc + hh * math.copysign(abs(s) ** (2 / e), s)
        pts.append((x, y, z))
    return pts


def loft(m, rings, mat, mats=None):
    """Closed tube through rings (lists of xyz with the same count), capped both ends."""
    vr = [[m.bm.verts.new(p) for p in r] for r in rings]
    n = len(vr[0])
    for k, (a, b) in enumerate(zip(vr, vr[1:])):
        mk = mats[k] if mats else mat
        for i in range(n):
            j = (i + 1) % n
            m.face((a[i], a[j], b[j], b[i]), mk)
    m.face(vr[0], mats[0] if mats else mat)
    m.face(list(reversed(vr[-1])), mats[-1] if mats else mat)
    return vr


def hull(m, pts, mat):
    """Convex hull of points (chamfered blocks)."""
    bm = m.bm
    verts = [bm.verts.new(p) for p in pts]
    res = bmesh.ops.convex_hull(bm, input=verts, use_existing_faces=False)
    junk = list({g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
    if junk:
        bmesh.ops.delete(bm, geom=junk, context="VERTS")
    live = [v for v in verts if v.is_valid]
    faces = list({f for v in live for f in v.link_faces})
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1.0), verts=live,
                             edges=list({e for f in faces for e in f.edges}))
    live = [v for v in verts if v.is_valid]
    for f in {f for v in live for f in v.link_faces}:
        f.material_index = mat


def cbox(x0, x1, y0, y1, z0, z1, ch, z1b=None, chz=None):
    """Corner points of a chamfered box; the top may slope from z1 (y0 end) to z1b (y1 end)."""
    chz = ch if chz is None else chz
    z1b = z1 if z1b is None else z1b
    pts = []
    for x, sx in ((x0, 1), (x1, -1)):
        for y, sy in ((y0, 1), (y1, -1)):
            for zz, sz in ((z0, 1), (None, -1)):
                if zz is None:
                    zz = z1 if y == y0 else z1b
                pts += [(x + sx * ch, y, zz + sz * chz), (x, y + sy * ch, zz + sz * chz), (x + sx * ch, y + sy * ch, zz)]
    return pts


def dome(m, cx, cy, rx, ry, z0, h, mat, n=16, k=5, p=2.2, base=0.0):
    """A closed dome: superellipse plan rx x ry at z0 (with a short vertical skirt `base`), rising h."""
    rings = []
    if base > 0:
        rings.append([(cx + x, cy + y, z0 - base) for x, y in _plan(rx, ry, n, p)])
    for i in range(k + 1):
        phi = (math.pi / 2) * i / (k + 1)
        s = math.cos(phi)
        rings.append([(cx + x * s, cy + y * s, z0 + h * math.sin(phi)) for x, y in _plan(rx, ry, n, p)])
    vr = [[m.bm.verts.new(q) for q in r] for r in rings]
    apex = m.bm.verts.new((cx, cy, z0 + h))
    for a, b in zip(vr, vr[1:]):
        for i in range(n):
            j = (i + 1) % n
            m.face((a[i], a[j], b[j], b[i]), mat)
    for i in range(n):
        j = (i + 1) % n
        m.face((vr[-1][i], vr[-1][j], apex), mat)
    m.face(list(reversed(vr[0])), mat)


def _plan(rx, ry, n, p):
    out = []
    for i in range(n):
        t = 2 * math.pi * i / n
        c, s = math.cos(t), math.sin(t)
        out.append((rx * math.copysign(abs(c) ** (2 / p), c), ry * math.copysign(abs(s) ** (2 / p), s)))
    return out


def cyl(m, p0, p1, r, mat, n=8, r1=None):
    """A capped cylinder (or cone, r1) from p0 to p1."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    q = d.to_track_quat("Z", "Y")
    rot = q.to_matrix().to_4x4()
    mid = (p0 + p1) / 2
    res = bmesh.ops.create_cone(m.bm, cap_ends=True, cap_tris=False, segments=n, radius1=r,
                                radius2=r if r1 is None else r1, depth=d.length,
                                matrix=Matrix.Translation(mid) @ rot)
    for f in {f for v in res["verts"] for f in v.link_faces}:
        f.material_index = mat


def mirror(fn):
    for s in (-1, 1):
        fn(s)




def sez(hw, zb, zt, dx, p):
    """Top height of a ring(hw, zb, zt, p) section at |dx| from its centre."""
    t = min(abs(dx) / hw, 1.0)
    zc, hh = (zb + zt) / 2, (zt - zb) / 2
    return zc + hh * (1 - t ** p) ** (1 / p)


def interp(prof, y):
    """Linear interpolation of a profile [(y, a, b, ...)] at y."""
    for a, b in zip(prof, prof[1:]):
        if a[0] <= y <= b[0]:
            t = (y - a[0]) / (b[0] - a[0])
            return [u + (v - u) * t for u, v in zip(a[1:], b[1:])]
    return list(prof[0][1:] if y < prof[0][0] else prof[-1][1:])


# --- the carapace: a faired armoured shell, flat-crowned, its belly a plain round dome -----------
# (y, half width, top z, bottom z); hw from the inner mask (row 9: 5 px, row 10: 6, rows 11-14: 7)
CAR = [(8.72, 0.7, 2.9, 1.7), (8.85, 2.7, 3.15, 1.0), (9.05, 4.25, 3.32, 0.7), (9.45, 5.05, 3.42, 0.5),
       (10.2, 6.0, 3.48, 0.4), (11.0, 6.8, 3.5, 0.35), (11.6, 7.02, 3.5, 0.35), (13.85, 7.02, 3.5, 0.35),
       (14.3, 6.97, 3.38, 0.4), (14.9, 6.72, 3.15, 0.55), (15.3, 6.05, 2.78, 0.8), (15.5, 4.6, 2.35, 1.2),
       (15.62, 1.6, 2.0, 1.5)]
CAR_P, CAR_PB = 3.0, 2.0


def car_z(x, y):
    hw, zt, zb = interp(CAR, y)
    return sez(hw, zb, zt, x, CAR_P)


def build_carapace(m):
    rings = [ring(0.0, y, hw, zb, zt, n=40, p=CAR_P, pb=CAR_PB, hwb=hw * 0.85) for y, hw, zt, zb in CAR]
    mats = [SEAM if (a[0] + b[0]) / 2 > 13.9 else SHELL for a, b in zip(CAR, CAR[1:])]
    loft(m, rings, SHELL, mats=mats + [SEAM])
    # the dark channel between the ribs (cols 11-12, rows 9-13)
    for f in m.bm.faces:
        c = f.calc_center_median()
        if abs(c.x) < 1.2 and c.y < 14.0 and c.z > 2.6:
            f.material_index = CHANNEL
    # machined detail: two hex bolts on each flank
    for s in (-1, 1):
        for y in (11.6, 13.2):
            x = s * 5.4
            z = car_z(x, y)
            cyl(m, (x, y, z - 0.3), (x, y, z + 0.08), 0.24, BOLT, n=6)


# --- the ribs: rounded rails from the humps at the notch (row 8, cols 8-10) back to row 14 --------
# (y, centre x (west rib), half width, top z, bottom z: the humps run down the carapace's nose)
RIB_PROF = [(7.88, -2.4, 0.18, 3.3, 2.0), (7.97, -2.42, 0.6, 3.8, 1.75), (8.12, -2.45, 1.05, 4.12, 1.55),
            (8.4, -2.5, 1.4, 4.4, 1.5), (9.0, -2.45, 1.48, 4.52, 1.6), (9.8, -2.3, 1.36, 4.48, 2.3),
            (10.8, -2.1, 1.1, 4.36, 2.4), (12.0, -2.0, 1.0, 4.26, 2.4), (13.4, -2.0, 0.95, 4.16, 2.4),
            (14.3, -2.0, 0.9, 3.92, 2.4), (14.85, -2.0, 0.65, 3.6, 2.4), (15.05, -2.0, 0.3, 3.35, 2.5)]


def build_ribs(m):
    for s in (-1, 1):
        rings = [ring(-s * cx, y, hw, zb, zt, n=20, p=3.2, pb=2.2) for y, cx, hw, zt, zb in RIB_PROF]
        loft(m, rings, RIB)


# --- the prongs: two hover nacelles and the snout, a belly keel between them ----------------------
# nacelle (west): (y, centre x, half width, centre z, half height)
LEG_PROF = [(14.3, -5.0, 1.3, 2.0, 0.95), (14.8, -4.97, 1.95, 2.0, 1.45), (16.4, -4.95, 1.97, 2.0, 1.5),
            (17.4, -4.55, 1.52, 1.98, 1.45), (21.5, -4.5, 1.5, 1.95, 1.4), (22.6, -4.75, 1.35, 1.9, 1.3),
            (23.3, -5.0, 1.1, 1.85, 1.1), (23.72, -5.05, 0.72, 1.8, 0.76), (23.95, -5.05, 0.25, 1.8, 0.3)]
LEG_P = 2.4


def leg_z(x, y):
    cx, hw, zc, hh = interp(LEG_PROF, y)
    return sez(hw, zc - hh, zc + hh, x - cx, LEG_P)


def build_legs(m):
    for s in (-1, 1):
        rings = [ring(s * cx, y, hw, zc - hh, zc + hh, n=24, p=LEG_P, pb=2.0) for y, cx, hw, zc, hh in LEG_PROF]
        loft(m, rings, LEG)
        # a joint collar where the nacelle leaves the carapace (row 15)
        cr = []
        for y, d in ((15.2, -0.05), (15.3, 0.12), (15.8, 0.12), (15.9, -0.05)):
            cx, hw, zc, hh = interp(LEG_PROF, y)
            cr.append(ring(s * cx, y, hw + d, zc - hh - d, zc + hh + d, n=24, p=LEG_P, pb=2.0))
        loft(m, cr, BOLT)
        # the light bezels along the slanting row (the lenses are frame parts)
        for x, y in LIGHT_POS:
            z = leg_z(x, y)
            dome(m, x if s < 0 else -x, y, 0.62, 0.62, z - 0.35, 0.47, HOUSING, n=14, k=3, p=2.0)


# snout: (y, half width, top z, bottom z)
SNOUT_PROF = [(13.8, 1.5, 3.25, 1.0), (14.3, 1.98, 3.72, 0.8), (17.0, 2.0, 3.72, 0.8), (21.0, 1.95, 3.35, 0.8),
              (22.0, 1.4, 2.95, 1.0), (22.6, 0.95, 2.55, 1.25), (22.95, 0.4, 2.15, 1.6)]
SNOUT_P = 2.4


def build_snout(m):
    rings = [ring(0.0, y, hw, zb, zt, n=24, p=SNOUT_P, pb=2.0) for y, hw, zt, zb in SNOUT_PROF]
    loft(m, rings, SNOUT)
    # the spine running into the vent (cols 11-12, rows 14-18 bright)
    hull(m, cbox(-0.95, 0.95, 16.6, 18.95, 3.2, 3.9, 0.25, z1b=3.88), SNOUT)
    # the vent housing (rows 18-20: 115 at cols 10/13 row 18, full row 19, cols 11-12 row 20)
    poly = [(-2.0, 17.85), (2.0, 17.85), (2.0, 19.95), (1.1, 21.05), (-1.1, 21.05), (-2.0, 19.95)]
    hull(m, [(x, y, z) for x, y in poly for z in (2.55, 3.58)], SNOUT)
    inner = [(-1.8, 18.0), (1.8, 18.0), (1.8, 19.88), (0.98, 20.88), (-0.98, 20.88), (-1.8, 19.88)]
    hull(m, [(x, y, z) for x, y in inner for z in (3.4, 3.72)], VENT)
    dome(m, 0.0, 20.0, 0.95, 0.75, 3.62, 0.26, VCORE, n=16, k=3, p=2.0)
    dome(m, 0.0, 19.4, 0.62, 0.5, 3.64, 0.32, VHEART, n=12, k=3, p=2.0)


# belly keel between the prongs: shows in the slots (cols 9 / 14, rows 15-21); plain closed shape
KEEL = [(14.5, 4.0, 2.2, 0.6), (21.4, 4.0, 2.2, 0.6), (21.85, 3.4, 1.95, 0.9), (22.05, 2.4, 1.6, 1.1)]


def build_keel(m):
    rings = [ring(0.0, y, hw, zb, zt, n=24, p=2.2) for y, hw, zt, zb in KEEL]
    loft(m, rings, CHASSIS)


def build_body():
    m = Mesh()
    build_carapace(m)
    build_ribs(m)
    build_legs(m)
    build_snout(m)
    build_keel(m)
    return m


# the nacelle lights (west nacelle; mirrored), top to bottom along the slanting row, by frame
LIGHT_POS = [(-3.5, 20.5), (-4.5, 21.5), (-5.5, 22.5)]
LIGHTS = {229: (L113, L114, L116), 231: (L115, L116, L118), 233: (L117, L121, L120)}


def build_lights(frame):
    m = Mesh()
    for s in (-1, 1):
        for (x, y), mat in zip(LIGHT_POS, LIGHTS[frame]):
            z = leg_z(x, y)
            dome(m, x if s < 0 else -x, y, 0.45, 0.45, z - 0.2, 0.42, mat, n=12, k=3, p=2.0)
    return m


def to_object(m, name, mats, coll, sharp=32):
    bm = m.bm
    # sprite px -> Blender units: X = (x + 0.5) / 12, Y = (14 - y) / 12, Z = z / 12
    T = Matrix(((PX, 0, 0, (AXU - 12) * PX), (0, -PX, 0, 14 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=T, verts=bm.verts)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4], quad_method="BEAUTY",
                          ngon_method="BEAUTY")
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for mt in mats:
        me.materials.append(mt)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(sharp))
    return obj


def materials(sprite):
    out = []
    for i in range(len(MATS)):
        pal, met, rough, em = MATS[i]
        tag = f"{NAME}_A_{i}"
        mt = common.palette_material(sprite, pal, tag, metallic=met, roughness=rough, emission_strength=em)
        if i in STEEL:
            bsdf = next(n for n in mt.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
            if "Specular IOR Level" in bsdf.inputs:
                bsdf.inputs["Specular IOR Level"].default_value = STEEL_SPEC
        out.append(mt)
    return out

# --- bake (AO + edge lift, roughness/metal), after usp_talon.bake_maps / newshe-155 ----------------

def bake_maps(obj, out_dir, prefix, textured, size=512, samples=64):
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
    except Exception as err:  # noqa: BLE001
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
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.02, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.02)
    bpy.ops.object.mode_set(mode="OBJECT")
    col_img = bpy.data.images.new(f"{prefix}_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new(f"{prefix}_rm", size // 2, size // 2, alpha=False)
    rm_img.colorspace_settings.name = "Non-Color"
    b0 = next(n for n in me.materials[0].node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    for img, c in ((col_img, (*TINT, 1.0)),
                   (rm_img, (1.0, b0.inputs["Roughness"].default_value, b0.inputs["Metallic"].default_value, 1.0))):
        img.pixels.foreach_set([v for _ in range(img.size[0] * img.size[1]) for v in c])
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

        def math_(op, a, b=None):
            n = node("ShaderNodeMath")
            n.operation = op
            for k, v in enumerate((a, b)):
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
        ao_l.inputs["Distance"].default_value = 0.14
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
                                       math_("MULTIPLY", edge, 0.15)), 1.0)
            tint = node("ShaderNodeCombineColor")
            for k in range(3):
                nt.links.new(math_("MULTIPLY", v, TINT[k]), tint.inputs[k])
            nt.links.new(tint.outputs[0], em.inputs["Color"])
        else:
            r = math_("ADD", rough, math_("SUBTRACT", math_("MULTIPLY", math_("SUBTRACT", 1.0, occl), 0.3),
                                          math_("MULTIPLY", edge, 0.12)))
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
        bpy.ops.object.bake(type="EMIT", margin=16, margin_type="EXTEND", use_clear=False)
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
    # per-object copies of the materials, so each frame wires its own maps
    for i in textured:
        m = mats[i].copy()
        me.materials[i] = m
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


# --- measure -----------------------------------------------------------------------------------

def measure(frame_objs, sprite, sub=8):
    import sprite_mask as SM
    from mathutils.bvhtree import BVHTree
    res = {}
    W, H = 24, 28
    for frame, objs in frame_objs.items():
        fr = next(f for f in sprite["frames"] if f["index"] == frame)
        pix = fr["pixels"]
        bm = bmesh.new()
        offs = []
        for o in objs:
            tmp = bmesh.new()
            tmp.from_mesh(o.data)
            tmp.transform(o.matrix_world)
            me = bpy.data.meshes.new("m_tmp")
            tmp.to_mesh(me)
            tmp.free()
            offs.append((len(bm.faces), o))
            bm.from_mesh(me)
            bpy.data.meshes.remove(me)
        bm.faces.ensure_lookup_table()
        tree = BVHTree.FromBMesh(bm)
        fmat = [f.material_index for f in bm.faces]
        top = [[False] * (W * sub) for _ in range(H * sub)]
        regions = {}
        for r in range(H):
            for c in range(W):
                counts = {}
                for j in range(sub):
                    for i in range(sub):
                        u, v = c + (i + 0.5) / sub, r + (j + 0.5) / sub
                        hit = tree.ray_cast(Vector(((u - 12) * PX, (14 - v) * PX, 5.0)), Vector((0, 0, -1)), 20.0)
                        if hit[0] is not None:
                            top[r * sub + j][c * sub + i] = True
                            counts[fmat[hit[2]]] = counts.get(fmat[hit[2]], 0) + 1
                if sum(counts.values()) >= sub * sub / 2 and pix[r][c] >= 0:
                    mi = max(counts, key=counts.get)
                    regions.setdefault(mi, []).append(pix[r][c])
        bm.free()
        idx, colors = SM.load(NAME, frame)
        mk = SM.masks(idx, colors)
        meas = SM.measure(mk, top)
        reg = {}
        for mi, vals in regions.items():
            pal = MATS[mi][0]
            sv = sorted(vals)
            lo, hi = len(sv) // 6, len(sv) - len(sv) // 6
            trimmed = sv[lo:hi] or sv
            reg[f"{mi}:pal{pal}"] = {"n": len(vals), "median_trim": trimmed[len(trimmed) // 2], "pixels": sv}
        grid = ["".join("#" if sum(top[r * sub + j][c * sub + i] for j in range(sub) for i in range(sub)) >= sub * sub / 2
                        else "." for c in range(W)) for r in range(H)]
        res[frame] = {**meas, "regions": reg, "top": grid}
    return res


# --- renders ------------------------------------------------------------------------------------

def _camera(name, loc, look, ortho=None, lens=None, up_y=False):
    data = bpy.data.cameras.new(name)
    if ortho:
        data.type = "ORTHO"
        data.ortho_scale = ortho
    else:
        data.lens = lens or 50
    cam = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = loc
    d = Vector(look) - Vector(loc)
    cam.rotation_euler = (0, 0, 0) if up_y else d.to_track_quat("-Z", "Y").to_euler()
    return cam


def _render(cam, path, w, h):
    sc = bpy.context.scene
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.render.resolution_percentage = 100
    sc.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def render_all(frame_objs, all_objs, out):
    out.mkdir(parents=True, exist_ok=True)
    sc = bpy.context.scene
    try:
        sc.render.engine = "BLENDER_EEVEE"
    except TypeError as err:
        sc.render.engine = next(e for e in str(err).replace("'", " ").replace(",", " ").split() if "EEVEE" in e)
    sc.render.film_transparent = True
    sc.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("w")
    sc.world = world
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.5, 0.52, 0.58, 1)
    bg.inputs[1].default_value = 0.9
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 3.2
    sc.collection.objects.link(sun)
    sun.rotation_euler = Vector((-0.35, 0.5, 1.0)).normalized().to_track_quat("Z", "Y").to_euler()
    gm = bpy.data.meshes.new("ground")
    gbm = bmesh.new()
    bmesh.ops.create_grid(gbm, x_segments=1, y_segments=1, size=3.0)
    bmesh.ops.translate(gbm, vec=(0, 0, -0.35), verts=gbm.verts)   # it hovers: ground well below
    gbm.to_mesh(gm)
    gbm.free()
    ground = bpy.data.objects.new("ground", gm)
    gm.materials.append(common.material("ground_mat", (0.13, 0.12, 0.1), roughness=0.9))
    sc.collection.objects.link(ground)
    C = Vector(((AXU - 12) * PX, (14 - CY) * PX, 0.2))
    views = {
        "top": ((C.x, 0, 10), (C.x, 0, 0), 2.0, None, True),
        "side": ((8, 0, C.z), (0, 0, C.z), 1.7, None, False),
        "front": ((C.x, -8, C.z), (C.x, 0, C.z), 1.7, None, False),
        "rear": ((C.x, 8, C.z), (C.x, 0, C.z), 1.7, None, False),
        "q_front": ((2.4, -2.9, 2.5), tuple(C), None, 60, False),
        "q_rear": ((-2.6, 2.6, 2.3), tuple(C), None, 60, False),
        "under": ((1.2, -1.8, -2.7), tuple(C), None, 55, False),
    }
    tilt = math.radians(32)
    dist = 9.0
    views["game"] = ((C.x, -dist * math.sin(tilt), dist * math.cos(tilt)), (C.x, 0, 0), None, 150, False)
    for frame, objs in frame_objs.items():
        for o in all_objs:
            o.hide_render = o not in objs
        for vn, (loc, look, ortho, lens, upy) in views.items():
            if frame != FRAMES[0] and vn not in ("top", "game", "q_front"):
                continue
            ground.hide_render = vn != "game"
            cam = _camera(f"c_{vn}", loc, look, ortho=ortho, lens=lens, up_y=upy)
            _render(cam, out / f"{vn}-{frame}.png", 480, 480)
        ground.hide_render = False
        cam = _camera("c_small", views["game"][0], views["game"][1], lens=150)
        _render(cam, out / f"gamesmall-{frame}.png", 80, 80)
    print("rendered", out)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    opt = lambda k, d=None: argv[argv.index(k) + 1] if k in argv else d  # noqa: E731
    sprite = common.load_sprite(WT, NAME)
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    coll = common.reset_collection(NAME)
    mats = materials(sprite)
    body = to_object(build_body(), NAME, mats, coll)
    lights = {f: to_object(build_lights(f), f"{NAME}-lights-{f}", mats, coll, sharp=80) for f in FRAMES}
    for o in [body, *lights.values()]:
        o.data.calc_loop_triangles()
        print(f"{o.name}: {len(o.data.loop_triangles)} triangles")
    # outline shell from the closed, unbaked body (D51, D90/D118: sealed before anything else)
    shell = common.outline_shell(body, coll, voxel=0.01, faces=900, smooth=6, inside=0.004)
    shell.name = shell.data.name = f"{NAME}_outline"
    fmt = "AUTO"
    if "--no-bake" not in argv:
        import tempfile
        bdir = Path(tempfile.mkdtemp(prefix="nsh229_bake_"))
        for o in coll.objects:
            o.hide_render = o is not body
        bake_maps(body, bdir, "pod229A_body", [i for i in MATS if i not in GLOW])
        for o in coll.objects:
            o.hide_render = False
        fmt = "WEBP"
    for f, o in lights.items():
        common.frame_part(o, [f])
    export = [body, shell, *lights.values()]
    if "--out" in argv:
        glb = Path(opt("--out"))
        common.export_glb(export, glb, image_format=fmt)
    else:
        common.export_sprite_model(WT, export, f"enemies/{NAME}", sprite["sprites"], image_format=fmt)
    frame_objs = {f: [body, lights[f]] for f in FRAMES}
    if "--measure" in argv:
        res = measure(frame_objs, sprite)
        Path(opt("--measure")).write_text(json.dumps(res, indent=1))
        for f, r in res.items():
            print("MEASURE", f, "iou_rule_grid", r["iou_rule_grid"], "iou_rule", r["iou_rule"],
                  {k: v["median_trim"] for k, v in r["regions"].items()})
    if "--render" in argv:
        render_all(frame_objs, [body, shell, *lights.values()], Path(opt("--render")))


if __name__ == "__main__":
    main()
