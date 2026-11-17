"""tyrend.anm, episode 3's ending (`]A[`), re-created as a 3D scene (DECISIONS.md D219).

The original is a 111-frame pre-rendered CG animation at 320x200, shown at ~9.94 frames a second
(playAnim("tyrend.anm", 0, 7): seven 14.375 ms periods a frame, 11.17 s). This scene follows it
shot for shot, timed in the original's frames (`t`, 0..111), rendered three video frames to each:

  A   0-31  A still camera on the stars and the green planet; a rounded olive-brown hull (the
            escape pod, with its lavender window band and portholes) sweeps in from the right,
            passes just under the camera and leaves bottom left.
  B  32-55  The slim grey-green fighter (the player's ship) dives in from the top right and levels
            out in the middle of the frame, flying left, its port wing hanging toward the camera.
  C  55-81  The camera chases it: the stars streak, the planet slides behind the hull, the camera
            closes in along the port side (green and red running lights) to the engine.
  D  81-95  The four nozzles light as a 2x2 cluster; the camera falls back to the rear quarter.
  E  95-111 The camera stops (the stars are still again) and the ship shrinks into the distance,
            a white-hot engine in an orange halo.

Run from the repository root (Blender 4.2+, EEVEE):

    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \\
        --python assets/blender/cutscenes/tyrend.py -- [--out DIR] [--scale S] [--frames 0,20,40] \\
        [--samples N] [--encode]

writes DIR/f_0001.png .. f_0333.png (default DIR: /tmp/tyrend-frames), at 1600x1000 times
--scale. --frames renders only those original frames (one video frame each, for comparing with
the original). --encode then makes public/art/cutscenes/tyrend.webm (VP9) with ffmpeg.
"""

import math
import random
import subprocess
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "art"))
import common as c  # noqa: E402  (assets/art/common.py: scene, model and node helpers)

ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default=None):
    return ARGV[ARGV.index(name) + 1] if name in ARGV else default


OUT_DIR = Path(arg("--out", "/tmp/tyrend-frames"))
SCALE = float(arg("--scale", "1"))
SAMPLES = int(arg("--samples", "24"))
ONLY = [float(v) for v in arg("--frames", "").split(",") if v != ""]
ENCODE = "--encode" in ARGV
WEBM = c.ROOT / "public" / "art" / "cutscenes" / "tyrend.webm"

WIDTH, HEIGHT = 1600, 1000  # the original's 8:5
FRAMES = 111  # the frames playAnim shows (recordCount - 1)
STEP = 3  # video frames per original frame
# playAnim's frame: setFrameCount(7) at the Normal speed's period, 0x4300 PIT cycles (vga.ts).
ANIM_FRAME_S = 7 * 0x4300 / (315_000_000 / 88 / 3)
FPS = STEP / ANIM_FRAME_S  # ~29.81

SKY = c.srgb(3, 3, 10)

scene = c.new_scene(engine="BLENDER_EEVEE", samples=SAMPLES)
scene.render.resolution_x, scene.render.resolution_y = WIDTH, HEIGHT
scene.render.resolution_percentage = round(100 * SCALE)
scene.render.fps = 30
scene.render.fps_base = 30 / FPS
scene.frame_start, scene.frame_end = 1, FRAMES * STEP
scene.view_settings.view_transform = "Standard"
scene.render.use_motion_blur = True
scene.render.motion_blur_shutter = 0.9
try:
    scene.eevee.motion_blur_steps = 4
except AttributeError:
    pass
c.world_color(SKY)


def frame_of(t):
    """The video frame showing original frame `t` (fractional between)."""
    return 1 + t * STEP


# --- Paths: control points in original frames, Catmull-Rom between, a key every video frame -------

class Path3:
    """A curve through [(t, value)]: Catmull-Rom between points (values are tuples of floats);
    before the first and after the last it holds."""

    def __init__(self, points):
        self.points = sorted((t, tuple(v) if isinstance(v, (tuple, list)) else (v,)) for t, v in points)

    def __call__(self, t):
        p = self.points
        if t <= p[0][0]:
            return p[0][1]
        if t >= p[-1][0]:
            return p[-1][1]
        i = max(k for k in range(len(p) - 1) if p[k][0] <= t)
        (t0, v0), (t1, v1) = p[i], p[i + 1]
        u = (t - t0) / (t1 - t0)
        # tangents (per unit u), zero at the ends so moves ease in and out
        def tangent(k):
            if k <= 0 or k >= len(p) - 1:
                return tuple(0.0 for _ in p[k][1])
            (ta, va), (tb, vb) = p[k - 1], p[k + 1]
            return tuple((b - a) / (tb - ta) for a, b in zip(va, vb))
        m0 = tuple(x * (t1 - t0) for x in tangent(i))
        m1 = tuple(x * (t1 - t0) for x in tangent(i + 1))
        h00, h10, h01, h11 = 2 * u**3 - 3 * u**2 + 1, u**3 - 2 * u**2 + u, -2 * u**3 + 3 * u**2, u**3 - u**2
        return tuple(h00 * a + h10 * ma + h01 * b + h11 * mb for a, ma, b, mb in zip(v0, m0, v1, m1))


def key_every_frame(obj, fn):
    """fn(t) sets the object's channels for original frame t; keyed on every video frame, linear."""
    for f in range(scene.frame_start, scene.frame_end + 1):
        fn((f - 1) / STEP)
        for path in ("location", "rotation_quaternion", "scale"):
            obj.keyframe_insert(path, frame=f)
    if obj.animation_data and obj.animation_data.action:
        linear(obj.animation_data.action)


def linear(action):
    curves = []
    try:
        curves = list(action.fcurves)
    except AttributeError:  # Blender 5: layered actions
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    curves += list(bag.fcurves)
    for fc in curves:
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"


def look_quat(eye, target, roll_deg=0.0, up=(0, 0, 1)):
    """A camera's rotation looking from eye to target, +Y up as near `up` as possible, rolled."""
    fwd = (Vector(target) - Vector(eye)).normalized()
    right = fwd.cross(Vector(up)).normalized()
    upv = right.cross(fwd)
    m = Matrix((right, upv, -fwd)).transposed()
    return m.to_quaternion() @ Quaternion((0, 0, 1), math.radians(roll_deg))


def ship_quat(heading_deg, pitch_deg, bank_deg):
    """A model's rotation (nose +Y, top +Z): turned to `heading` (degrees from +Y toward -X),
    nose raised by `pitch`, rolled by `bank` (positive: the port wing, its -X, goes down)."""
    return (Quaternion((0, 0, 1), math.radians(heading_deg))
            @ Quaternion((1, 0, 0), math.radians(pitch_deg))
            @ Quaternion((0, 1, 0), -math.radians(bank_deg)))


# --- The sky: stars and the planet ---------------------------------------------------------------

STAR_R = 1500.0
rng = random.Random(1)


# Two populations, like the original's field (~770 specks a frame over a dithered haze of dim ones):
# (count, sizes in degrees, brightness range).
STAR_LAYERS = [
    (22000, (0.07, 0.085, 0.1, 0.12, 0.14), (0.35, 1.0)),
    (60000, (0.05, 0.06), (0.08, 0.3)),
]


def build_stars(layers=STAR_LAYERS):
    """Small quads facing the centre on a sphere around the camera, each its own colour and
    brightness (white, lavender, pink, like the original's specks)."""
    import bmesh
    bm = bmesh.new()
    col = bm.loops.layers.color.new("star")
    tints = [(1, 1, 1), (0.82, 0.82, 1.0), (1.0, 0.84, 0.92), (0.8, 0.9, 1.0)]
    for count, sizes, (lo, hi) in layers:
        for _ in range(count):
            z = rng.uniform(-1, 1)
            a = rng.uniform(0, 2 * math.pi)
            d = Vector((math.sqrt(1 - z * z) * math.cos(a), math.sqrt(1 - z * z) * math.sin(a), z))
            p = d * STAR_R
            size = STAR_R * math.radians(rng.choice(sizes))
            u = d.orthogonal().normalized() * size / 2
            v = d.cross(u).normalized() * size / 2
            verts = [bm.verts.new(p + s * u + r * v) for s, r in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
            face = bm.faces.new(verts)
            b = lo + (hi - lo) * rng.random() ** 1.8
            tint = rng.choice(tints)
            for loop in face.loops:
                loop[col] = (tint[0] * b, tint[1] * b, tint[2] * b, 1)
    mesh = bpy.data.meshes.new("stars")
    bm.to_mesh(mesh)
    bm.free()
    mat = bpy.data.materials.new("stars")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = c.node(nt, "ShaderNodeOutputMaterial")
    attr = c.node(nt, "ShaderNodeVertexColor", p_layer_name="star")
    em = c.node(nt, "ShaderNodeEmission", Strength=2.2)
    c.link(nt, attr.outputs["Color"], em.inputs["Color"])
    c.link(nt, em.outputs[0], out.inputs["Surface"])
    obj = c.mesh_object("stars", mesh, mat)
    obj.rotation_mode = "QUATERNION"
    return obj, em


stars, star_emission = build_stars()

# The planet: mint green, mottled with darker green, lit from the upper right; fixed in the sky at
# the top left of the opening shot, ~8.5 degrees across.
LENS, SENSOR = 35.0, 36.0
TAN_H = SENSOR / 2 / LENS  # tan of half the horizontal field
TAN_V = TAN_H * HEIGHT / WIDTH
PLANET_D = 1000.0


def sky_dir(px, py):
    """The opening camera's (looking +Y, level) world direction through original pixel (px, py)."""
    return Vector(((px - 160) / 160 * TAN_H, 1.0, (100 - py) / 100 * TAN_V)).normalized()


planet_mat = bpy.data.materials.new("planet")
planet_mat.use_nodes = True
nt = planet_mat.node_tree
bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
bsdf.inputs["Roughness"].default_value = 0.9
tc = c.node(nt, "ShaderNodeTexCoord")
noise = c.node(nt, "ShaderNodeTexNoise", Scale=2.6, Detail=9.0, Roughness=0.62, Distortion=0.35)
c.link(nt, tc.outputs["Object"], noise.inputs["Vector"])
blot = c.ramp(nt, [(0.38, c.srgb(60, 112, 84)), (0.5, c.srgb(118, 178, 128)), (0.62, c.srgb(150, 222, 170))])
c.link(nt, noise.outputs["Fac"], blot.inputs["Fac"])
c.link(nt, blot.outputs["Color"], bsdf.inputs["Base Color"])
bump = c.node(nt, "ShaderNodeBump", Strength=0.25)
c.link(nt, noise.outputs["Fac"], bump.inputs["Height"])
c.link(nt, bump.outputs[0], bsdf.inputs["Normal"])
bpy.ops.mesh.primitive_uv_sphere_add(segments=96, ring_count=48)
planet = bpy.context.active_object
planet.name = "planet"
planet.data.materials.append(planet_mat)
c.smooth(planet)
PLANET_AT = sky_dir(67, 49) * PLANET_D
planet.location = PLANET_AT
planet.scale = [PLANET_D * math.tan(math.radians(8.6 / 2))] * 3

# Light: a sun from the upper right, a little in front (the planet's lit limb), a dim blue fill.
sun = c.light("SUN", (0, 0, 0), target=(-0.55, 0.35, -0.6), energy=4.2, color=(1.0, 0.97, 0.92))
fill = c.light("SUN", (0, 0, 0), target=(0.5, -0.2, 0.4), energy=0.5, color=(0.6, 0.7, 1.0))
# The planet's own light, so its terminator falls lower left as in the original.
planet_sun = c.light("SUN", (0, 0, 0), target=(-0.8, 0.45, -0.5), energy=3.2)

# --- Glows: camera-facing quads, additive, a soft radial falloff ----------------------------------


def glow(name, color, radius, strength, power=2.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    try:
        mat.surface_render_method = "BLENDED"
    except AttributeError:
        mat.blend_method = "BLEND"
    nt = mat.node_tree
    nt.nodes.clear()
    out = c.node(nt, "ShaderNodeOutputMaterial")
    tc = c.node(nt, "ShaderNodeTexCoord")
    grad = c.node(nt, "ShaderNodeTexGradient", p_gradient_type="SPHERICAL")
    c.link(nt, tc.outputs["Object"], grad.inputs["Vector"])
    pw = c.node(nt, "ShaderNodeMath", p_operation="POWER", values={1: power})
    c.link(nt, grad.outputs["Fac"], pw.inputs[0])
    k = c.node(nt, "ShaderNodeMath", p_operation="MULTIPLY", values={1: strength})
    c.link(nt, pw.outputs[0], k.inputs[0])
    em = c.node(nt, "ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1)
    c.link(nt, k.outputs[0], em.inputs["Strength"])
    add = c.node(nt, "ShaderNodeAddShader")
    c.link(nt, em.outputs[0], add.inputs[0])
    c.link(nt, c.node(nt, "ShaderNodeBsdfTransparent").outputs[0], add.inputs[1])
    c.link(nt, add.outputs[0], out.inputs["Surface"])
    bpy.ops.mesh.primitive_plane_add(size=2)
    obj = bpy.context.active_object
    obj.name = name
    obj.data.materials.append(mat)
    obj.scale = (radius, radius, radius)
    con = obj.constraints.new("COPY_ROTATION")
    con.target = None  # set once the camera exists
    obj["strength_input"] = k.name
    return obj, k.inputs[1]


# --- The ships ----------------------------------------------------------------------------------
# Both built for this scene from the original's frames (tyrend_models.py): the game has no model of
# either (the player ships and the Talon read as different ships here; D219).

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tyrend_models as models  # noqa: E402

pod = models.build_hull()
fighter, POINTS = models.build_fighter()
ENGINE = POINTS["engine"]
NOSE_LIGHT = POINTS["nose_light"]
WING_LIGHT = POINTS["starboard_tip"]


def attach(obj, root, local):
    obj.parent = root
    obj.location = local
    return obj


flame, flame_k = glow("flame", c.srgb(255, 236, 196), 0.2, 0.0, power=1.2)
# The four nozzles light as a 2x2 cluster, each its own white-hot disc.
nozzle_glows = [glow(f"nozzle_{i}", c.srgb(255, 214, 160), 0.06, 0.0, power=0.8) for i in range(4)]
halo, halo_k = glow("halo", c.srgb(255, 150, 70), 0.55, 0.0, power=3.0)
red_light, red_k = glow("red_light", c.srgb(255, 90, 70), 0.05, 5.0, power=2.2)
red_halo, red_halo_k = glow("red_halo", c.srgb(220, 80, 40), 0.35, 0.0, power=2.0)
green_light, green_k = glow("green_light", c.srgb(90, 255, 120), 0.08, 6.0, power=2.2)
for g, at in ((flame, ENGINE), (halo, ENGINE), (red_light, NOSE_LIGHT), (red_halo, NOSE_LIGHT), (green_light, WING_LIGHT),
              *((g, at) for (g, _), at in zip(nozzle_glows, POINTS["nozzles"]))):
    attach(g, fighter, at)

# --- Camera ---------------------------------------------------------------------------------------

cam = c.camera((0, 0, 0), (0, 1, 0), lens=LENS)
cam.data.sensor_width = SENSOR
cam.data.sensor_fit = "HORIZONTAL"
cam.data.clip_start = 0.02
cam.data.clip_end = 5000
cam.rotation_mode = "QUATERNION"
for g in (flame, halo, red_light, red_halo, green_light, *(g for g, _ in nozzle_glows)):
    g.constraints[0].target = cam

# --- The shots ------------------------------------------------------------------------------------
# Shots A and B: the camera stays at the origin looking +Y, drifting a few degrees left and up
# (the planet creeps right and down by ~17 x 10 original pixels by frame 55).
CAM_YAW = Path3([(0, 0.0), (55, 2.6)])  # degrees, left
CAM_PITCH = Path3([(0, 0.0), (55, 1.5)])  # degrees, up

# A: the pod, nose first (heading 90: nose toward -X), from the right edge to under the camera.
POD_POS = Path3([
    (2, (19.0, 22.0, -0.9)),
    (4, (15.5, 18.5, -0.9)),
    (8, (9.2, 12.6, -0.9)),
    (12, (5.6, 9.0, -0.85)),
    (16, (3.0, 6.6, -0.8)),
    (20, (0.6, 5.0, -0.8)),
    (24, (-1.8, 4.3, -0.85)),
    (28, (-4.2, 3.7, -0.95)),
    (33, (-7.5, 3.1, -1.1)),
])
POD_ROT = Path3([(2, (96, 2, 10)), (20, (100, 3, 14)), (33, (104, 4, 18))])  # heading, pitch, bank
POD_SCALE = 1.0

# B..E: the fighter. B is in the opening camera's space; from 55 the camera is placed relative to
# the ship, which flies along -X (heading 90).
FIGHTER_POS = Path3([
    (31, (2.6, 2.3, 1.2)),
    (36, (1.7, 2.2, 0.8)),
    (40, (1.05, 2.5, 0.42)),
    (46, (0.6, 3.6, 0.42)),
    (52, (0.05, 4.3, 0.26)),
    (55, (0.0, 4.4, 0.24)),
])
# E: from 95 the ship flies straight away from the held camera, along its line of sight.
AWAY = Path3([(95, 0.0), (100, 0.9), (105, 2.0), (111, 3.5)])
FIGHTER_ROT = Path3([
    (31, (115, -14, 66)),
    (40, (108, -10, 60)),
    (48, (96, -4, 42)),
    (55, (92, -2, 38)),
    (70, (90, 0, 30)),
    (84, (90, 0, 28)),
    (96, (90, 0, 26)),
    (111, (90, 0, 26)),
])

# From 55 the camera's eye and target relative to the ship's position (world axes: the ship's nose
# is -X, its port side -Y, toward the opening camera).
CAM_REL = Path3([
    (55, (0.0, -4.4, -0.24)),
    (60, (0.05, -3.8, -0.1)),
    (64, (0.1, -3.2, 0.0)),
    (70, (0.25, -2.2, 0.1)),
    (76, (0.42, -1.6, 0.12)),
    (81, (0.55, -1.5, 0.12)),
    (85, (1.8, -1.6, 0.6)),
    (90, (2.5, -1.5, 0.4)),
    (95, (3.1, -1.25, 0.3)),
])
CAM_AIM = Path3([  # the point looked at, relative to the ship
    (55, (0.0, 0.0, 0.0)),
    (64, (0.0, 0.0, 0.0)),
    (70, (0.15, 0.0, 0.0)),
    (76, (0.42, 0.0, 0.0)),
    (81, (0.5, 0.0, 0.0)),
    (85, (0.3, 0.0, 0.0)),
    (95, (0.6, 0.0, 0.0)),
])
# The ship turns left while the camera chases it (the sky swings right behind it: the planet
# passes behind the hull and leaves the frame by 70), degrees about the vertical.
SWING = Path3([(55, 0.0), (58, 9.0), (62, 24.0), (64, 34.0), (66, 42.0), (70, 56.0), (81, 66.0), (95, 72.0)])
CAM_ROLL = Path3([(55, 0.0), (81, -4.0), (85, 10.0), (95, 30.0)])
# E: from 95 the camera holds where it was; the ship leaves along -X.

# The stars' streak: the sky turns about the vertical (degrees a frame) while the camera chases.
STREAK = Path3([(55, 0.0), (58, 4.5), (80, 5.0), (90, 4.0), (94.6, 3.5), (95.0, 0.0)])

# Flame and glows (strengths) over time.
FLAME = Path3([(81, 0.0), (82, 3.0), (84, 6.0), (111, 8.0)])
HALO = Path3([(81, 0.0), (84, 0.2), (95, 0.24), (100, 0.28), (111, 0.32)])
RED_HALO = Path3([(84, 0.0), (88, 1.4), (98, 1.2), (104, 0.0)])
GREEN = Path3([(55, 6.0), (78, 6.0), (82, 0.0)])
FLAME_SIZE = Path3([(84, 0.1), (95, 0.14), (111, 0.26)])  # the core between the nozzles, swelling
NOZZLE_SIZE = Path3([(81, 0.03), (84, 0.075), (95, 0.085), (111, 0.12)])  # the four discs merge far off
HALO_SIZE = Path3([(84, 0.6), (95, 0.9), (111, 1.4)])  # the halo stays big on screen as the ship shrinks


def opening_cam(t):
    q = Quaternion((0, 0, 1), math.radians(CAM_YAW(t)[0])) @ Quaternion((1, 0, 0), math.radians(90 + CAM_PITCH(t)[0]))
    return Vector((0, 0, 0)), q


cam_hold = {}


def camera_at(t):
    if t <= 55:
        return opening_cam(t)
    tt = min(t, 95.0)
    ship = Vector(FIGHTER_POS(tt))
    turn = Quaternion((0, 0, 1), math.radians(SWING(tt)[0]))
    eye = ship + turn @ Vector(CAM_REL(tt))
    aim = ship + turn @ Vector(CAM_AIM(tt))
    q = look_quat(eye, aim, CAM_ROLL(tt)[0])
    if t > 55 and t < 60:  # blend out of the opening camera's slight drift
        _, q0 = opening_cam(55)
        u = (t - 55) / 5
        q = q0.slerp(q, u * u * (3 - 2 * u))
    return eye, q


def set_camera(t):
    eye, q = camera_at(t)
    cam.location = eye
    cam.rotation_quaternion = q


def set_pod(t):
    pod.location = POD_POS(t)
    h, p, b = POD_ROT(t)
    pod.rotation_quaternion = ship_quat(h, p, b)
    pod.scale = [POD_SCALE] * 3


def fighter_at(t):
    if t <= 95:
        return Vector(FIGHTER_POS(t))
    eye, q = camera_at(95)
    fwd = q @ Vector((0, 0, -1))
    return Vector(FIGHTER_POS(95)) + fwd * AWAY(t)[0]


def set_fighter(t):
    fighter.location = fighter_at(t)
    h, p, b = FIGHTER_ROT(t)
    fighter.rotation_quaternion = ship_quat(h + SWING(min(t, 95.0))[0], p, b)
    fighter.scale = (1, 1, 1)


streak_angle = {}
acc = 0.0
for f in range(scene.frame_start, scene.frame_end + 1):
    t = (f - 1) / STEP
    streak_angle[f] = acc
    acc += STREAK(t)[0] / STEP


def set_stars(t):
    f = round(t * STEP) + 1
    eye, _ = camera_at(t)
    stars.location = eye
    stars.rotation_quaternion = Quaternion((0, 0, 1), -math.radians(streak_angle.get(f, 0.0)))
    stars.scale = (1, 1, 1)


key_every_frame(cam, set_camera)
key_every_frame(pod, set_pod)
key_every_frame(fighter, set_fighter)
key_every_frame(stars, set_stars)


def show_between(root, t0, t1):
    """Render `root`'s model only from original frame t0 to t1."""
    for o in [root, *root.children_recursive]:
        if o.get("tyrian_outline"):
            continue
        for f in (scene.frame_start, round(frame_of(t0)), round(frame_of(t1)) + 1):
            o.hide_render = not (round(frame_of(t0)) <= f <= round(frame_of(t1)))
            o.keyframe_insert("hide_render", frame=f)


show_between(pod, 2, 33)
show_between(fighter, 30, FRAMES)

# Glow strengths, keyed as material values.
for f in range(scene.frame_start, scene.frame_end + 1):
    halo.scale = [HALO_SIZE((f - 1) / STEP)[0]] * 3
    halo.keyframe_insert("scale", frame=f)
    flame.scale = [FLAME_SIZE((f - 1) / STEP)[0]] * 3
    flame.keyframe_insert("scale", frame=f)
    for g, _ in nozzle_glows:
        g.scale = [NOZZLE_SIZE((f - 1) / STEP)[0]] * 3
        g.keyframe_insert("scale", frame=f)
for sock, path, base in ((flame_k, FLAME, 1.0), (halo_k, HALO, 1.0), (red_halo_k, RED_HALO, 1.0), (green_k, GREEN, 1.0),
                         *((k, FLAME, 1.6) for _, k in nozzle_glows)):
    for f in range(scene.frame_start, scene.frame_end + 1):
        sock.default_value = path((f - 1) / STEP)[0] * base
        sock.keyframe_insert("default_value", frame=f)
# The streaking stars are spread over their streak: brighten them as they streak.
for f in range(scene.frame_start, scene.frame_end + 1):
    s = STREAK((f - 1) / STEP)[0]
    star_emission.inputs["Strength"].default_value = 2.2 * (1 + 2.2 * s)
    star_emission.inputs["Strength"].keyframe_insert("default_value", frame=f)
for m in bpy.data.materials:
    if m.node_tree and m.node_tree.animation_data and m.node_tree.animation_data.action:
        linear(m.node_tree.animation_data.action)

# --- Render ---------------------------------------------------------------------------------------

OUT_DIR.mkdir(parents=True, exist_ok=True)
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGB"
if ONLY:
    for t in ONLY:
        f = round(frame_of(t))
        scene.frame_set(f)
        scene.render.filepath = str(OUT_DIR / f"t_{t:05.1f}.png")
        bpy.ops.render.render(write_still=True)
else:
    scene.render.filepath = str(OUT_DIR / "f_")
    bpy.ops.render.render(animation=True)
    if ENCODE:
        WEBM.parent.mkdir(parents=True, exist_ok=True)
        cmd = ["ffmpeg", "-y", "-framerate", f"{FPS:.6f}", "-start_number", "1", "-i", str(OUT_DIR / "f_%04d.png"),
               "-c:v", "libvpx-vp9", "-b:v", "0", "-crf", arg("--crf", "44"), "-row-mt", "1", "-pix_fmt", "yuv420p",
               "-an", str(WEBM)]
        print(" ".join(cmd))
        subprocess.run(cmd, check=True)
