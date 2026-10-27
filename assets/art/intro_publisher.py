"""Picture 10: the first intro card (`intro_logos`, mainint.c), the publisher's logo.

The original is a chrome logo hanging in a blue sky of sunlit clouds, the sun blazing above it.
The logo is the publisher's own, so this keeps the sky, the sun and the chrome but makes the
emblem the USP Talon: a mirror-chrome Talon, nose up, on a chrome hexagon, with no lettering. Writes public/art/intro_publisher.webp.
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as c  # noqa: E402

NAME = "intro_publisher"
bpy = c.bpy

c.new_scene(samples=128)

# The sky: a backdrop far behind, blue-violet, with banks of cloud and the sun's rays.
sky = bpy.data.materials.new("sky")
sky.use_nodes = True
nt = sky.node_tree
nt.nodes.clear()
out = c.node(nt, "ShaderNodeOutputMaterial")
tc = c.node(nt, "ShaderNodeTexCoord")
sep = c.node(nt, "ShaderNodeSeparateXYZ")
c.link(nt, tc.outputs["UV"], sep.inputs[0])
grad = c.ramp(nt, [(0.0, c.srgb(120, 130, 200)), (0.6, c.srgb(60, 70, 150)), (1.0, c.srgb(36, 40, 110))])
c.link(nt, sep.outputs["Y"], grad.inputs["Fac"])
# Clouds: billowing noise, stretched sideways, thresholded into soft white banks.
cm = c.node(nt, "ShaderNodeMapping")
cm.inputs["Scale"].default_value = (2.0, 5.0, 1.0)
c.link(nt, tc.outputs["UV"], cm.inputs["Vector"])
cn = c.node(nt, "ShaderNodeTexNoise", Scale=2.2, Detail=14.0, Roughness=0.62, Distortion=0.3)
c.link(nt, cm.outputs[0], cn.inputs["Vector"])
cover = c.node(nt, "ShaderNodeMapRange", **{"From Min": 0.48, "From Max": 0.72, "To Min": 0.0, "To Max": 1.0})
c.link(nt, cn.outputs["Fac"], cover.inputs["Value"])
cloud = c.node(nt, "ShaderNodeMix", p_data_type="RGBA")
c.link(nt, cover.outputs[0], cloud.inputs[0])
c.link(nt, grad.outputs["Color"], cloud.inputs[6])
cloud.inputs[7].default_value = (*c.srgb(235, 235, 255), 1)
# The sun: a hot disc at the top centre with a starburst of rays.
sun_at = c.node(nt, "ShaderNodeMapping")
sun_at.inputs["Location"].default_value = (-0.5, -0.86, 0)
c.link(nt, tc.outputs["UV"], sun_at.inputs["Vector"])
asp = c.node(nt, "ShaderNodeVectorMath", p_operation="MULTIPLY")
asp.inputs[1].default_value = (1.6, 1.0, 1.0)  # the backdrop is 8:5
c.link(nt, sun_at.outputs[0], asp.inputs[0])
dist = c.node(nt, "ShaderNodeVectorMath", p_operation="LENGTH")
c.link(nt, asp.outputs[0], dist.inputs[0])
core = c.node(nt, "ShaderNodeMapRange", **{"From Min": 0.0, "From Max": 0.11, "To Min": 8.0, "To Max": 0.0})
core.interpolation_type = "SMOOTHSTEP"
c.link(nt, dist.outputs["Value"], core.inputs["Value"])
sx = c.node(nt, "ShaderNodeSeparateXYZ")
c.link(nt, asp.outputs[0], sx.inputs[0])
ang = c.node(nt, "ShaderNodeMath", p_operation="ARCTAN2")
c.link(nt, sx.outputs["Y"], ang.inputs[0])
c.link(nt, sx.outputs["X"], ang.inputs[1])
rays_n = c.node(nt, "ShaderNodeTexNoise", Scale=9.0, Detail=2.0)
rays_n.noise_dimensions = "1D"
c.link(nt, ang.outputs[0], rays_n.inputs["W"])
rays = c.node(nt, "ShaderNodeMapRange", **{"From Min": 0.58, "From Max": 0.8, "To Min": 0.0, "To Max": 1.0})
c.link(nt, rays_n.outputs["Fac"], rays.inputs["Value"])
reach = c.node(nt, "ShaderNodeMapRange", **{"From Min": 0.05, "From Max": 0.5, "To Min": 1.0, "To Max": 0.0})
c.link(nt, dist.outputs["Value"], reach.inputs["Value"])
rmul = c.node(nt, "ShaderNodeMath", p_operation="MULTIPLY")
c.link(nt, rays.outputs[0], rmul.inputs[0])
c.link(nt, reach.outputs[0], rmul.inputs[1])
glow = c.node(nt, "ShaderNodeMath", p_operation="ADD")
c.link(nt, rmul.outputs[0], glow.inputs[0])
c.link(nt, core.outputs[0], glow.inputs[1])
sun_col = c.node(nt, "ShaderNodeMix", p_data_type="RGBA", p_blend_type="ADD")
c.link(nt, glow.outputs[0], sun_col.inputs[0])
c.link(nt, cloud.outputs[2], sun_col.inputs[6])
sun_col.inputs[7].default_value = (1.0, 0.97, 0.9, 1)
em = c.node(nt, "ShaderNodeEmission", Strength=1.0)
c.link(nt, sun_col.outputs[2], em.inputs["Color"])
c.link(nt, em.outputs[0], out.inputs["Surface"])

backdrop = c.primitive("plane", "sky", sky, size=1.0)
backdrop.scale = (64, 40, 1)
backdrop.location = (0, 30, 0)
backdrop.rotation_euler = (math.radians(90), 0, 0)
# The same sky all round, for the chrome to reflect.
c.world_color(c.srgb(90, 100, 180), 1.0)

chrome = c.material("chrome", (0.62, 0.65, 0.8), metallic=1.0, roughness=0.18)
dark_chrome = c.material("dark_chrome", (0.22, 0.24, 0.36), metallic=1.0, roughness=0.3)

# The plate: a dark chrome hexagon standing in the sky, in a bright chrome rim.
plate = c.primitive("cylinder", "plate", dark_chrome, vertices=6, radius=3.0, depth=0.5)
plate.rotation_euler = (math.radians(90), 0, math.radians(0))
plate.location = (0, 2.1, 0.2)
bev = plate.modifiers.new("bevel", "BEVEL")
bev.width = 0.15
bev.segments = 3
ring = c.primitive("cylinder", "ring", chrome, vertices=6, radius=3.5, depth=0.35)
ring.rotation_euler = (math.radians(90), 0, 0)
ring.location = (0, 2.35, 0.2)
bev = ring.modifiers.new("bevel", "BEVEL")
bev.width = 0.12
bev.segments = 3
# A long rail through it, catching the sun.
rail = c.primitive("cube", "rail", chrome, size=1.0)
rail.scale = (13.0, 0.3, 0.22)
rail.location = (0, 2.0, -2.2)
bev = rail.modifiers.new("bevel", "BEVEL")
bev.width = 0.06

# The emblem on the plate: the Talon in chrome, nose up.
talon = c.model("usp_talon", location=(0, 1.5, 0.2), scale=2.1)
c.aim(talon, (0, 0, 1), (0, -1, 0))
for m in c.model_materials(talon):
    b = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if b and not m.name.startswith("engine"):
        # Chrome, keeping a trace of the sprite's tone in the darker parts.
        col = b.inputs["Base Color"].default_value
        lum = 0.3 * col[0] + 0.6 * col[1] + 0.1 * col[2]
        b.inputs["Base Color"].default_value = (0.55 + lum, 0.58 + lum, 0.68 + lum, 1)
        b.inputs["Metallic"].default_value = 1.0
        b.inputs["Roughness"].default_value = 0.15

c.light("SUN", (0, 10, 12), (0, 0, 0), energy=4.0, color=c.srgb(255, 248, 235), angle=2)
c.light("AREA", (-4, -10, 6), (0, 2, 0.5), energy=300, color=c.srgb(170, 180, 255), size=10)

c.camera((0, -19, -2.0), (0, 2, 0.6), lens=45)
c.save(NAME)
