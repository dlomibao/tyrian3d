"""Picture 8: the end of episode 1, panned up to under "If not, things could become unpleasant."
(`]U 008`, levels1.dat section 42).

The original's warning is a flayed head impaled on a horn. Here the trophy is a wrecked USP Talon,
the player's own ship, skewered on a bloodied horn that rises out of a field of black spikes, a
bony spine coiled around the shaft. Behind it, the same violet sky with a vast dim planet on the
left and a small moon on the right. Writes public/art/story_skull.webp.
"""

import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as c  # noqa: E402

NAME = "story_skull"
bpy = c.bpy
random.seed(8)

c.new_scene(samples=128)

# Sky: violet, darkest overhead, with a faint glow along the horizon.
wnt = bpy.context.scene.world.node_tree
bg = next(n for n in wnt.nodes if n.type == "BACKGROUND")
tc = c.node(wnt, "ShaderNodeTexCoord")
sep = c.node(wnt, "ShaderNodeSeparateXYZ")
c.link(wnt, tc.outputs["Generated"], sep.inputs[0])
sky = c.ramp(wnt, [(0.0, c.srgb(64, 26, 74)), (0.12, c.srgb(44, 16, 54)), (0.45, c.srgb(16, 5, 22))])
c.link(wnt, sep.outputs["Z"], sky.inputs["Fac"])
c.link(wnt, sky.outputs["Color"], bg.inputs["Color"])

# The planet: huge and dim, behind the horn on the left; and a small moon on the right.
def body(name, radius, location, color, glow):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = c.node(nt, "ShaderNodeOutputMaterial")
    # Lit from the right: the normal's x, broken up by noise.
    geo = c.node(nt, "ShaderNodeNewGeometry")
    lw = c.node(nt, "ShaderNodeSeparateXYZ")
    c.link(nt, geo.outputs["Normal"], lw.inputs[0])
    noise = c.node(nt, "ShaderNodeTexNoise", Scale=3.0, Detail=6.0)
    noise.inputs["Roughness"].default_value = 0.6
    shade = c.ramp(nt, [(0.0, color), (1.0, glow)])
    mixf = c.node(nt, "ShaderNodeMath", p_operation="MULTIPLY_ADD", values={2: 0.25})
    c.link(nt, lw.outputs["X"], mixf.inputs[0])
    c.link(nt, noise.outputs["Fac"], mixf.inputs[1])
    c.link(nt, mixf.outputs[0], shade.inputs["Fac"])
    em = c.node(nt, "ShaderNodeEmission", Strength=1.0)
    c.link(nt, shade.outputs["Color"], em.inputs["Color"])
    c.link(nt, em.outputs[0], out.inputs["Surface"])
    obj = c.primitive("uv_sphere", name, mat, segments=96, ring_count=48, radius=radius)
    c.smooth(obj)
    obj.location = location
    return obj

body("planet", 34, (-30, 140, 20), c.srgb(30, 10, 38), c.srgb(110, 50, 124))
body("moon", 4.2, (34, 120, 9), c.srgb(50, 20, 60), c.srgb(120, 60, 130))

# The spike field: black thorns of every height along the horizon.
black = c.emission("black", (0.0, 0.0, 0.0), 0.0)  # pure silhouettes
for i in range(320):
    x = random.uniform(-48, 48)
    y = random.uniform(12, 60)
    h = random.uniform(1.5, 5.5) * (2.2 if random.random() < 0.15 else 1.0) * (0.6 + y / 60)
    spike = c.primitive("cone", f"spike{i}", black, vertices=8, radius1=random.uniform(0.25, 0.8), radius2=0.0, depth=h)
    spike.location = (x, y, h / 2 - 0.6)
    spike.rotation_euler = (random.uniform(-0.25, 0.25), random.uniform(-0.35, 0.35), 0)
ground = c.primitive("plane", "ground", black, size=300)
ground.location = (0, 0, -0.5)

# The horn: a curved, ridged tusk, bone at the base and bloodied toward the tip.
horn_mat = bpy.data.materials.new("horn")
horn_mat.use_nodes = True
nt = horn_mat.node_tree
bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
bsdf.inputs["Roughness"].default_value = 0.35
tc = c.node(nt, "ShaderNodeTexCoord")
sep = c.node(nt, "ShaderNodeSeparateXYZ")
c.link(nt, tc.outputs["Generated"], sep.inputs[0])
warp = c.node(nt, "ShaderNodeTexNoise", Scale=6.0, Detail=6.0)
c.link(nt, tc.outputs["Object"], warp.inputs["Vector"])
height = c.node(nt, "ShaderNodeMath", p_operation="ADD")
c.link(nt, sep.outputs["Z"], height.inputs[0])
scaled = c.node(nt, "ShaderNodeMath", p_operation="MULTIPLY", values={1: 0.25})
c.link(nt, warp.outputs["Fac"], scaled.inputs[0])
c.link(nt, scaled.outputs[0], height.inputs[1])
hcol = c.ramp(nt, [(0.2, c.srgb(70, 60, 52)), (0.5, c.srgb(120, 96, 80)), (0.62, c.srgb(110, 20, 16)), (0.9, c.srgb(60, 6, 6))])
c.link(nt, height.outputs[0], hcol.inputs["Fac"])
c.link(nt, hcol.outputs["Color"], bsdf.inputs["Base Color"])
ridges = c.node(nt, "ShaderNodeTexWave", Scale=3.0, Distortion=4.0, **{"Detail": 4.0})
ridges.wave_type = "RINGS"
c.link(nt, tc.outputs["Object"], ridges.inputs["Vector"])
hb = c.node(nt, "ShaderNodeBump", Strength=0.3)
c.link(nt, ridges.outputs["Fac"], hb.inputs["Height"])
c.link(nt, hb.outputs[0], bsdf.inputs["Normal"])

horn = c.primitive("cone", "horn", horn_mat, vertices=48, radius1=0.42, radius2=0.0, depth=9.0)
horn.location = (0, 6, 4.0)
horn.rotation_euler = (0, math.radians(-4), 0)
sub = horn.modifiers.new("loops", "SUBSURF")
sub.levels = sub.render_levels = 2
sub.subdivision_type = "SIMPLE"
c.smooth(horn)

# The wreck: the Talon, nose down, run through by the horn, scorched.
talon = c.model("usp_talon", scale=1.15)
talon.location = (-0.02, 5.8, 4.4)
c.aim(talon, (0.3, -0.15, -1.0), (0.1, -1.0, 0.1))
c.tint_model(talon, metallic=0.5, roughness=0.6, darken=0.75, glow=0.0)
# Blood and oil running down the shaft below it.
drip = c.material("drip", c.srgb(70, 4, 4), roughness=0.15)
for i in range(4):
    d = c.primitive("uv_sphere", f"drip{i}", drip, segments=16, ring_count=8, radius=0.09)
    d.scale = (1, 1, 3.5)
    d.location = (random.uniform(-0.2, 0.2) - 0.05, 5.62, 3.2 - i * 0.55)

# The spine: a ridged, tapering tail coiled up around the horn.
bone = c.material("bone", c.srgb(62, 50, 44), roughness=0.45)
curve = bpy.data.curves.new("spine", "CURVE")
curve.dimensions = "3D"
curve.bevel_depth = 0.2
curve.bevel_resolution = 4
curve.use_fill_caps = True
spline = curve.splines.new("POLY")
N = 120
spline.points.add(N - 1)
for i, pt in enumerate(spline.points):
    t = i / (N - 1)
    a = t * 2.2 * 2 * math.pi
    r = 0.85 - 0.3 * t
    pt.co = (math.cos(a) * r, 6 + math.sin(a) * r * 0.8, 0.3 + t * 3.3, 1)
    # Ridged like vertebrae, thinning toward the top.
    pt.radius = (1.0 - 0.6 * t) * (0.8 + 0.25 * math.cos(i * 1.6))
spine = bpy.data.objects.new("spine", curve)
bpy.context.scene.collection.objects.link(spine)
curve.materials.append(bone)

# A cold rim light from behind and a red key from the front right, as in the original.
c.light("SUN", (-2, 30, 6), (0, 6, 4), energy=3.0, color=c.srgb(200, 160, 255), angle=3)
c.light("AREA", (5, -2, 7), (0, 6, 4), energy=260, color=c.srgb(255, 150, 140), size=3)

c.camera((0, -9.5, 3.4), (0, 6, 4.6), lens=38)
c.save(NAME)
