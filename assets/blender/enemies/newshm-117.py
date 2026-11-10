"""Spiral orb, newshm-117 (newshm.shp 117/119/121): a floating, coiled armoured ball.

What it is (behaviour, tyrian-scratch/object-audit): a MOVING ORB. Type 569 sweeps side to side at
up to 7 px/tick (mv 7,0, cyclic acceleration, explodes like an air enemy); 582 drifts at 5 px/tick;
in GAUNTLET it is pushed sideways 4 px/tick; in MINEMAZE it floats over the black void between the
rock walls. Its sprite grows 15 -> 17 -> 19 px and back (bobbing toward the camera, pulsing). So it is
a round ball with a round underside and no base plate, its height close to its width (D120's lesson:
name the object first). D121 built it as a flat snail-shell dome on a plinth; this rebuild keeps that
model's plan reading of the spiral and wraps it round an ellipsoid.

Reading of the sprite (24x28 px, a closed ink ring of 33 round a round mauve ball; the inner mask is
an ellipse, 13x14 px at frame 117, 15x16 at 119, 17x19 at 121, centred on column 11.5). The dark rim
and the bright upper-left spot are a lit sphere's shading and sheen, not paint:
- An inner whorl (the coil's apex) at the upper left (centre about (-0.25, -0.30) of the ball's half
  sizes, radius ~0.47): a dome standing a little proud of the ball, two spiral strips whose chamfered
  edges make one seam winding inward from where the band ends.
- A dark groove (the suture, palette 84/83/82) runs from the top edge down the inner whorl's right
  side and hooks left beneath it; it fades out at the lower left, where the whorls meet in a seam. Its
  floor is the ball's core, an ellipsoid one groove depth inside the surface.
- The outer whorl: one armoured band that wraps the inner whorl clockwise from the groove's top, a
  little crowned (lowest at the top right, fullest round the right and bottom) and running over the
  ball's shoulder down to its equator. Nine chamfered plates (transverse seams), a longitudinal seam
  along each plate's shoulder.
- Under the equator, a plain closed belly (the round underside, visible from the side at the tilted
  game camera; no detail).
Frames: the ball swells (each frame its own model: newshm-117, -f2, -f3) and darkens, one palette
step per frame on every part.

    blender --background --python assets/blender/enemies/newshm-117.py   (add -- --nobake to skip the AO/roughness bake)
Exports enemies/newshm-117, -f2, -f3 (frames 117, 119, 121), one model each.

Coordinates: c / r are sprite px (column, row from the top-left); X = (c - 12) / 12,
Y = (14 - r) / 12, Z = z / 12. Shape maths runs in the ball's normalised plan (u, v), v down; a
surface point is the ellipsoid's point over (u, v) pushed out along its radius by a relief in px.
"""

import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
import numpy as np

sys.path[:0] = [str(Path(__file__).resolve().parents[1])]
import common  # noqa: E402
import usp_talon as T  # noqa: E402

WT = common.repo_root(__file__)

NAME = "newshm-117"
PX = 1 / 12

# Per frame: plan centre (c, r) and half sizes in px (the inner mask's ellipse), relief scale, and
# the palette index per part (medians of the sprite's part pixels, shading and highlights left out).
FRAMES = [
    (117, dict(c=(11.5, 14.0), r=(6.5, 7.0), k=1.00, groove=84, band=90, boss=91)),
    (119, dict(c=(11.5, 14.0), r=(7.5, 8.0), k=1.12, groove=83, band=89, boss=90)),
    (121, dict(c=(11.5, 13.5), r=(8.5, 9.5), k=1.24, groove=81, band=87, boss=88)),
]
RIM = 1.02                    # plan scale of the equator (pixel-circle coverage fit)
HZ = 0.86                     # the ball's vertical half height / its mean plan half size
BELLY = 5.0                   # the underside's lowest point, px below the model origin (pass height)
GROOVE_D = 0.85               # groove depth below the ball's surface (px, frame 117)
BOSS = (-0.25, -0.30, 0.47, 0.45)   # inner whorl: centre u, v and radii (normalised, v down)
PSI0 = 31.0                   # band start angle round the boss centre (deg, 0 = right, 90 = up)
SPAN = 338.0                  # the band runs clockwise this far; the rest is the groove's top
N_PLATES = 9
SEAM = 0.32                   # transverse seam width at the rim (px)
TUCK = 104.0                  # polar angle (deg) where the band's outer edge tucks into the belly

# Band crown (px proud of the ball, frame 117) and groove half gap (normalised) along the band, t 0..1.
CROWN_T = T.pchip([0.0, 0.035, 0.1, 0.22, 0.42, 0.6, 0.78, 0.93, 1.0],
                  [0.2, 0.3, 0.45, 0.6, 0.62, 0.55, 0.42, 0.36, 0.32])
G_T = T.pchip([0.0, 0.36, 0.46, 0.56, 0.66, 1.0], [0.15, 0.15, 0.10, 0.045, 0.025, 0.025])
# Inner whorl relief over the ball (px, frame 117) by boss plan scale (0 apex, 1 its rim at the groove).
BOSS_REL = T.pchip([0.0, 0.2, 0.35, 0.5, 0.66, 0.8, 0.9, 0.97, 1.0],
                   [0.95, 0.92, 0.86, 0.76, 0.62, 0.46, 0.3, 0.12, 0.0])


class Frame:
    def __init__(self, f):
        self.cx, self.cy = f["c"]
        self.rx, self.ry = f["r"][0] * RIM, f["r"][1] * RIM
        self.k = f["k"]
        self.rz = HZ * (self.rx + self.ry) / 2
        self.zc = self.rz - BELLY

    def at(self, su, sv, ct, rel):
        """Ellipsoid point (plan su, sv on the unit sphere's plan, cos of the polar angle ct), pushed
        out along its radius by rel px (scaled by the frame's k) -> Blender coordinates."""
        p = np.array((su * self.rx, sv * self.ry, ct * self.rz))
        n = float(np.linalg.norm(p))
        if n > 1e-9:
            p *= 1 + rel * self.k / n
        c, r, z = self.cx + p[0], self.cy + p[1], self.zc + p[2]
        return ((c - 12) * PX, (14 - r) * PX, z * PX)

    def up(self, u, v, rel):
        """Upper-surface point over plan (u, v) (clamped to the equator)."""
        rho = math.hypot(u, v)
        if rho > 1:
            u, v, rho = u / rho, v / rho, 1.0
        return self.at(u, v, math.sqrt(max(0.0, 1 - rho * rho)), rel)

    def dn(self, u, v, theta, rel):
        """Point at polar angle theta (deg, 90 = equator) in plan direction (u, v)."""
        rho = math.hypot(u, v) or 1.0
        st, ct = math.sin(math.radians(theta)), math.cos(math.radians(theta))
        return self.at(u / rho * st, v / rho * st, ct, rel)


def dirv(psi):
    a = math.radians(psi)
    return math.cos(a), -math.sin(a)


def boss_r(psi):
    a = math.radians(psi)
    return 1 / math.sqrt((math.cos(a) / BOSS[2]) ** 2 + (math.sin(a) / BOSS[3]) ** 2)


def rim_hit(psi, rho):
    """Distance from the boss centre along psi to the circle |p| = rho (normalised plan)."""
    du, dv = dirv(psi)
    bu, bv = BOSS[0], BOSS[1]
    bd = bu * du + bv * dv
    return -bd + math.sqrt(bd * bd - (bu * bu + bv * bv) + rho * rho)


def ring_faces(bm, rings, mat, closed_loop=True, cap=True):
    """Bridge rings (lists of verts, equal length) into quads; cap the first and last rings."""
    faces = []
    m = len(rings[0])
    for a, b in zip(rings, rings[1:]):
        for i in range(m if closed_loop else m - 1):
            j = (i + 1) % m
            f = bm.faces.new((a[i], a[j], b[j], b[i]))
            f.material_index = mat
            faces.append(f)
    if cap:
        for ring in (rings[0], rings[-1]):
            f = bm.faces.new(ring)
            f.material_index = mat
            faces.append(f)
    return faces


# --- parts ----------------------------------------------------------------------------------------

def build_ellipsoid(bm, F, mat, rel, th0, th1, n=64, m=32, cap=False):
    """A band of the ellipsoid (relief rel) from polar angle th0 to th1 (deg). th0 = 0 closes the top
    with a pole; th1 = 180 the bottom; cap closes an open lower edge with a flat disc."""
    rings = []
    js = range(m + 1)
    for j in js:
        th = th0 + (th1 - th0) * j / m
        if th <= 1e-6 or th >= 180 - 1e-6:
            rings.append(None)
            continue
        rings.append([bm.verts.new(F.dn(math.cos(2 * math.pi * i / n), math.sin(2 * math.pi * i / n), th, rel))
                      for i in range(n)])
    pole_top = bm.verts.new(F.at(0, 0, 1, rel)) if rings[0] is None else None
    pole_bot = bm.verts.new(F.at(0, 0, -1, rel)) if rings[-1] is None else None
    body = [r for r in rings if r is not None]
    for a, b in zip(body, body[1:]):
        for i in range(n):
            k = (i + 1) % n
            bm.faces.new((a[i], a[k], b[k], b[i])).material_index = mat
    if pole_top is not None:
        for i in range(n):
            bm.faces.new((body[0][(i + 1) % n], body[0][i], pole_top)).material_index = mat
    elif cap:
        bm.faces.new(list(reversed(body[0]))).material_index = mat
    if pole_bot is not None:
        for i in range(n):
            bm.faces.new((body[-1][i], body[-1][(i + 1) % n], pole_bot)).material_index = mat


def build_core(bm, F, mat):
    """The ball's core, one groove depth inside its surface: the groove's floor."""
    build_ellipsoid(bm, F, mat, -GROOVE_D, 0.0, 180.0, n=64, m=32)


def build_belly(bm, F, mat):
    """The round underside: the ellipsoid below the equator, closed with a disc at the equator."""
    build_ellipsoid(bm, F, mat, 0.0, 90.0, 180.0, n=64, m=14, cap=True)


def band_section(t, drop=0.0, notch=True):
    """Closed loop across the band at t: (s, relief px, polar angle or None). s = 0 inner edge (the
    groove), 1 the equator; None = the upper surface over the plan point."""
    c = float(CROWN_T(t))
    D = GROOVE_D
    d = lambda r, lo: max(lo, r - drop)  # noqa: E731 (chamfered plate ends drop the top surface)
    top = [
        (0.0, d(-D + 0.25, -D + 0.05)),
        (0.025, d(-D + 0.62 * (c + D), -D + 0.1)),
        (0.09, d(c - 0.22, -D + 0.15)),
        (0.2, d(c - 0.04, -D + 0.2)),
        (0.36, d(c, -D + 0.2)),
        (0.52, d(c - 0.07, -D + 0.2)),
        (0.6, d(c - 0.14, -D + 0.15)),
        (0.625, d(c - (0.3 if notch else 0.16), -D)),       # longitudinal seam (a shallow V notch)
        (0.65, d(c - 0.2, -D + 0.1)),
        (0.76, d(0.72 * c, -D + 0.15)),
        (0.88, d(0.38 * c, -D + 0.1)),
        (0.96, d(0.1 * c, -0.35)),
        (1.0, d(0.0, -0.3)),
    ]
    return ([(0.0, -D - 0.45, None)] + [(s, r, None) for s, r in top]
            + [(1.0, -0.25, TUCK), (0.45, -D - 0.7, None)])


def band_point(t, s, inset=0.0, shrink=0.0):
    psi = PSI0 - SPAN * t
    du, dv = dirv(psi)
    tc = min(1.0, max(0.0, t))
    r0 = boss_r(psi) + G_T(tc)
    r1 = rim_hit(psi, 1.0) - inset
    s = shrink + (1 - 2 * shrink) * s
    r = r0 + (r1 - r0) * s
    return BOSS[0] + du * r, BOSS[1] + dv * r


def band_vert(bm, F, t, s, rel, theta, inset=0.0, shrink=0.0):
    u, v = band_point(t, s, inset=inset, shrink=shrink)
    if theta is None:
        return bm.verts.new(F.up(u, v, rel))
    return bm.verts.new(F.dn(u, v, theta, rel))


# The coil's two free ends (at the notch, the sprite's dark top right): a chamfered scroll end cap,
# (t offset in chamfer widths, top drop px, plan shrink), end face first.
END_CAP = [(0.0, 0.55, 0.045), (0.35, 0.22, 0.018), (1.0, 0.0, 0.0)]
PLATE_CAP = [(0.0, 0.32, 0.0), (1.0, 0.0, 0.0)]


def build_band(bm, F, mat):
    rim_len = 2 * math.pi * 0.5 * (F.rx + F.ry) * SPAN / 360
    seam_t = SEAM / rim_len
    ch_t = 0.3 / rim_len
    end_t = 0.55 / rim_len
    for p in range(N_PLATES):
        ta = p / N_PLATES + (seam_t / 2 if p else 0)
        tb = (p + 1) / N_PLATES - (seam_t / 2 if p < N_PLATES - 1 else 0)
        ha, ca = (END_CAP, end_t) if p == 0 else (PLATE_CAP, ch_t)
        hb, cb = (END_CAP, end_t) if p == N_PLATES - 1 else (PLATE_CAP, ch_t)
        head = [(ta + k * ca, d, sh) for k, d, sh in ha]
        tail = [(tb - k * cb, d, sh) for k, d, sh in reversed(hb)]
        t0, t1 = head[-1][0], tail[0][0]
        steps = max(3, int((t1 - t0) * 40))
        ts = head + [(t0 + (t1 - t0) * i / steps, 0.0, 0.0) for i in range(1, steps)] + tail
        rings = []
        for t, drop, sh in ts:
            rings.append([band_vert(bm, F, t, s, r, th, shrink=sh) for s, r, th in band_section(t, drop)])
        ring_faces(bm, rings, mat)


SEAM_FLOOR = 0.42   # px below the plate tops: the floor of the transverse seams (a shallow groove)
FLOOR_KEEP = [0, 1, 3, 5, 7, 8, 10, 12, 13, 14, 15]   # section points kept under the plates


def build_band_floor(bm, F, mat, drop=SEAM_FLOOR, inset=0.01, t0=None):
    """One continuous strip under the nine plates, SEAM_FLOOR below their tops, so each transverse
    seam is a shallow groove with a floor and not a slot down to the core (which drew as ink).
    With drop 0, inset 0 and t0 0 it is the seamless band of the outline shell's source."""
    rim_len = 2 * math.pi * 0.5 * (F.rx + F.ry) * SPAN / 360
    seamless = drop == 0
    t0 = 0.55 / rim_len if t0 is None else t0
    t1 = 1.0 - (0.0 if seamless else 0.55 / rim_len)
    steps = 72 if seamless else 48
    rings = []
    for i in range(steps + 1):
        t = t0 + (t1 - t0) * i / steps
        sec = band_section(t, drop, notch=not seamless)
        if not seamless:
            sec = [sec[k] for k in FLOOR_KEEP]
        rings.append([band_vert(bm, F, t, inset + (1 - 2 * inset) * s, r, th) for s, r, th in sec])
    ring_faces(bm, rings, mat)


def boss_pt(F, s, a, rel):
    """Inner-whorl point at boss plan scale s and angle a (rad, round the boss centre)."""
    sh = (1 - s) * 0.06   # the apex sits a little right of and above the plan centre
    return F.up(BOSS[0] + sh + s * BOSS[2] * math.cos(a), BOSS[1] - sh - s * BOSS[3] * math.sin(a), rel)


def boss_rel(s):
    return float(BOSS_REL(max(0.0, min(1.0, s))))


def build_boss_floor(bm, F, mat, lift=-0.3, smax=0.95):
    """A dome under the boss's two spiral strips, a little below them: the coil seam's floor.
    With lift 0 and smax 1 it is the seamless boss of the outline shell's source."""
    n, m = 32, 6
    rings = [[bm.verts.new(boss_pt(F, smax, 2 * math.pi * i / n, -GROOVE_D - 0.4)) for i in range(n)]]
    for j in range(m):
        s = smax * (1 - j / m)
        rings.append([bm.verts.new(boss_pt(F, s, 2 * math.pi * i / n, boss_rel(s) + lift)) for i in range(n)])
    for a, b in zip(rings, rings[1:]):
        for i in range(n):
            k = (i + 1) % n
            bm.faces.new((a[i], a[k], b[k], b[i])).material_index = mat
    apex = bm.verts.new(boss_pt(F, 0.0, 0.0, boss_rel(0.0) + lift))
    for i in range(n):
        bm.faces.new((rings[-1][i], rings[-1][(i + 1) % n], apex)).material_index = mat
    bm.faces.new(list(reversed(rings[0]))).material_index = mat


SEAM_PHI0 = 53.0      # the boss's coil seam starts here (deg round the boss, where the band ends)
SEAM_S0, SEAM_S1 = 0.56, 0.12   # seam radius (boss plan scale) at the start and after one turn


def build_boss(bm, F, mat):
    """Inner whorl: the coil's apex as two closed spiral strips over one dome relief. Turn 1 runs
    clockwise from the band's end with the boss rim outside and the spiral seam inside; turn 2 fans
    from that seam to the apex. Their chamfered edges make one modelled seam winding inward."""
    gap, ch, drop = 0.018, 0.035, 0.24
    steps = 28

    def S(th):
        return SEAM_S0 + (SEAM_S1 - SEAM_S0) * th / (2 * math.pi)

    def strip(th0, th1, edges):
        rings = []
        for i in range(steps + 1):
            th = th0 + (th1 - th0) * i / steps
            a = math.radians(SEAM_PHI0) - th
            s_in, s_out = edges(th)
            ss = [s_in, s_in + ch] + [s_in + ch + (s_out - s_in - 2 * ch) * k / 4 for k in range(1, 4)] + [s_out - ch, s_out]
            rs = [boss_rel(x) for x in ss]
            if s_in > 0.01:
                rs[0] -= drop
            if s_out < 0.99:
                rs[-1] -= drop
            ring = [bm.verts.new(boss_pt(F, x, a, r)) for x, r in zip(ss, rs)]
            ring.append(bm.verts.new(boss_pt(F, s_out, a, -GROOVE_D - 0.5)))
            ring.append(bm.verts.new(boss_pt(F, s_in, a, -GROOVE_D - 0.5)))
            rings.append(ring)
        ring_faces(bm, rings, mat)

    strip(0.0, 2 * math.pi, lambda th: (S(th) + gap / 2, 1.0))
    strip(2 * math.pi, 4 * math.pi, lambda th: (0.0, S(th - 2 * math.pi) - gap / 2))


def build_shell_source(model, f, coll):
    """The outline shell's source: the ball without its seams (one seamless band, one boss dome).
    A voxel shell of the real model kept its plate seams as creases, and the inverted-hull outline
    inks every crease: thick black spokes across the band. Only the groove stays (the sprite's own
    dark groove)."""
    F = Frame(f)
    bm = bmesh.new()
    build_core(bm, F, 0)
    build_belly(bm, F, 0)
    build_band_floor(bm, F, 0, drop=0.0, inset=0.0, t0=0.0)
    build_boss_floor(bm, F, 0, lift=0.0, smax=1.0)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(model)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(model, me)
    coll.objects.link(obj)
    return obj


def build_frame(sprite, model, f, coll):
    F = Frame(f)
    mats = [common.palette_material(sprite, f[p], f"{model}_{p}", metallic=mt, roughness=ro)
            for p, mt, ro in (("groove", 0.12, 0.78), ("band", 0.4, 0.42), ("boss", 0.4, 0.38))]
    GROOVE, BAND, BOSSM = range(3)
    bm = bmesh.new()
    build_core(bm, F, GROOVE)
    build_belly(bm, F, BAND)
    build_band(bm, F, BAND)
    build_band_floor(bm, F, BAND)    # the seams' floor: band metal (a groove-coloured floor drew dark spokes)
    build_boss(bm, F, BOSSM)
    build_boss_floor(bm, F, GROOVE)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(model)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    obj = bpy.data.objects.new(model, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(34))
    return obj


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




def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    coll = common.reset_collection("newshm117")
    sprite = common.load_sprite(WT, NAME)
    base = sprite["sprites"][0]
    bake = "--nobake" not in argv
    bake_dir = tempfile.mkdtemp(prefix="n117_bake_")
    for i, (index, f) in enumerate(FRAMES):
        model = NAME if i == 0 else f"{NAME}-f{i + 1}"
        obj = build_frame(sprite, model, f, coll)
        print(f"{model}: {sum(len(p.vertices) - 2 for p in obj.data.polygons)} triangles")
        if bake:
            bake_maps(obj, bake_dir, model.replace("-", "_"))
        src = build_shell_source(f"{model}_shellsrc", f, coll)
        shell = common.outline_shell(src, coll, voxel=0.01, faces=1500, inside=0.006)
        bpy.data.objects.remove(src, do_unlink=True)
        bpy.context.view_layer.update()
        shell.name = f"{model}_outline"
        common.export_sprite_model(WT, [obj, shell], f"enemies/{model}", [dict(base, frames=[index])],
                                   image_format="WEBP" if bake else "AUTO")


main()
