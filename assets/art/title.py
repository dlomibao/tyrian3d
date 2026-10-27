"""Picture 4: the title screen (JE_loadPic 4 in titleScreen, mainint.c), drawn under the TYRIAN logo
and the menu.

The planet Tyrian seen from low orbit: its limb sweeps from the top left to the bottom right, red
continents under white cloud, a violet haze along the horizon, black space in the top right where
the logo sits. The original's red streaks in the bottom left become the USP Talon diving in with
its engines burning. Writes public/art/title.webp.
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as c  # noqa: E402

NAME = "title"
bpy = c.bpy

c.new_scene(samples=128, look="AgX - Punchy")

wnt = bpy.context.scene.world.node_tree
bg = next(n for n in wnt.nodes if n.type == "BACKGROUND")
coord = c.node(wnt, "ShaderNodeTexCoord")
stars = c.starfield(wnt, coord.outputs["Generated"], scale=600, density=0.012, strength=0.9)
c.link(wnt, stars.outputs[0], bg.inputs["Color"])

R = 10.0

# Ground: maroon lowlands and rust uplands, a little bump for relief.
ground = bpy.data.materials.new("ground")
ground.use_nodes = True
nt = ground.node_tree
bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
bsdf.inputs["Roughness"].default_value = 0.9
tc = c.node(nt, "ShaderNodeTexCoord")
land = c.node(nt, "ShaderNodeTexNoise", Scale=0.55, Detail=14.0, Roughness=0.62, Distortion=0.3)
c.link(nt, tc.outputs["Object"], land.inputs["Vector"])
lcol = c.ramp(nt, [
    (0.35, c.srgb(30, 3, 5)),
    (0.48, c.srgb(70, 10, 14)),
    (0.58, c.srgb(110, 26, 26)),
    (0.68, c.srgb(150, 70, 60)),
])
c.link(nt, land.outputs["Fac"], lcol.inputs["Fac"])
c.link(nt, lcol.outputs["Color"], bsdf.inputs["Base Color"])
bump = c.node(nt, "ShaderNodeBump", Strength=0.35, Distance=0.05)
c.link(nt, land.outputs["Fac"], bump.inputs["Height"])
c.link(nt, bump.outputs[0], bsdf.inputs["Normal"])
planet = c.primitive("uv_sphere", "planet", ground, segments=256, ring_count=128, radius=R)
c.smooth(planet)

# Clouds: a shell of white swirls (warped noise, thresholded) over the ground.
clouds = bpy.data.materials.new("clouds")
clouds.use_nodes = True
nt = clouds.node_tree
nt.nodes.clear()
out = c.node(nt, "ShaderNodeOutputMaterial")
tc = c.node(nt, "ShaderNodeTexCoord")
warp = c.node(nt, "ShaderNodeTexNoise", Scale=0.35, Detail=4.0)
c.link(nt, tc.outputs["Object"], warp.inputs["Vector"])
mixv = c.node(nt, "ShaderNodeMix", p_data_type="VECTOR", Factor=0.9)
c.link(nt, tc.outputs["Object"], mixv.inputs[4])
c.link(nt, warp.outputs["Color"], mixv.inputs[5])
cn = c.node(nt, "ShaderNodeTexNoise", Scale=0.62, Detail=12.0, Roughness=0.62, Distortion=0.4)
c.link(nt, mixv.outputs[1], cn.inputs["Vector"])
cover = c.node(nt, "ShaderNodeMapRange", **{"From Min": 0.53, "From Max": 0.6, "To Min": 0.0, "To Max": 1.0})
c.link(nt, cn.outputs["Fac"], cover.inputs["Value"])
white = c.node(nt, "ShaderNodeBsdfPrincipled", Roughness=1.0)
white.inputs["Base Color"].default_value = (1.0, 0.97, 1.0, 1)
transp = c.node(nt, "ShaderNodeBsdfTransparent")
mixs = c.node(nt, "ShaderNodeMixShader")
c.link(nt, cover.outputs[0], mixs.inputs["Fac"])
c.link(nt, transp.outputs[0], mixs.inputs[1])
c.link(nt, white.outputs[0], mixs.inputs[2])
c.link(nt, mixs.outputs[0], out.inputs["Surface"])
cloud_shell = c.primitive("uv_sphere", "clouds", clouds, segments=256, ring_count=128, radius=R * 1.004)
c.smooth(cloud_shell)

# Atmosphere: a violet glow that thickens toward the horizon.
haze = c.rim_glow("haze", c.srgb(190, 110, 235), strength=2.4, start=0.6, power=2.5)
atmo = c.primitive("uv_sphere", "atmosphere", haze, segments=256, ring_count=128, radius=R * 1.03)
c.smooth(atmo)

# Sunlight from beyond the upper right: the far limb is bright, the bottom left falls into dusk.
c.light("SUN", (7, -2, 8), (0, 0, 0), energy=3.6, color=c.srgb(255, 236, 220), angle=1.0)

# A faint fill from behind the viewer, so the night side and the ship keep some shape.
c.light("SUN", (-3, -16, 9), (0, 0, 0), energy=0.35, color=c.srgb(200, 190, 255))

# The Talon diving toward the planet, engines burning (the original's red streaks).
talon = c.model("usp_talon", scale=0.34)
for o in talon.children_recursive:
    o.visible_shadow = False  # it's far above the clouds: no shadow on them
c.tint_model(talon, metallic=0.6, roughness=0.35)
trail_mat = c.emission("trail", c.srgb(255, 70, 30), 3.0)
for i, dx in enumerate((-0.18, 0.18)):
    # A cone along +Z turned to trail behind the ship (-Y), wide at the nozzle.
    trail = c.primitive("cone", f"trail{i}", trail_mat, vertices=16, radius1=0.05, radius2=0.0, depth=5.0)
    trail.parent = talon
    trail.location = (dx, -0.9 - 2.5, 0)
    trail.rotation_euler = (math.radians(90), 0, 0)
    trail.visible_shadow = False

# Camera in low orbit over the top-left of the disc: the limb runs corner to corner.
cam = c.camera((-3.0, -16.5, 9.2), (1.2, 0.0, 6.0), lens=32)
c.bpy.context.view_layer.update()
# The Talon in the bottom left, its top to the camera (the sprite's view), nose down and right.
right, up, view = c.camera_axes(cam)
talon.location = cam.location + view * 8.0 - right * 2.2 - up * 0.9
c.aim(talon, right * 0.75 - up * 0.55 + view * 0.35, cam.location - talon.location)
c.save(NAME)
