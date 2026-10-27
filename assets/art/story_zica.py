"""Picture 13: episode 4, after the tunnel boss (`]P 013`, levels4.dat section 32), under the text
about transmitting the access codes that start re-heating the planet Zica.

The top two thirds are a red holo-grid screen for the text. Below it, framed by a glowing edge, a
figure works the controls of a heavy emplacement (a game turret, newshg-201) on Zica's frozen
surface, all in red light, with swirls of red mist off to the right.
Writes public/art/story_zica.webp.
"""

import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as c  # noqa: E402

NAME = "story_zica"
bpy = c.bpy
random.seed(13)

c.new_scene(samples=128)
c.world_color(c.srgb(40, 4, 4), 0.4)

RED = c.srgb(255, 40, 30)

# The ground: dark red rock under swirling mist.
ground_mat = bpy.data.materials.new("ground")
ground_mat.use_nodes = True
nt = ground_mat.node_tree
bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
bsdf.inputs["Roughness"].default_value = 0.6
tc = c.node(nt, "ShaderNodeTexCoord")
swirl = c.node(nt, "ShaderNodeTexNoise", Scale=0.18, Detail=6.0, Roughness=0.5, Distortion=1.5)
c.link(nt, tc.outputs["Object"], swirl.inputs["Vector"])
gcol = c.ramp(nt, [(0.35, c.srgb(20, 2, 2)), (0.55, c.srgb(70, 12, 10)), (0.75, c.srgb(150, 40, 34))])
c.link(nt, swirl.outputs["Fac"], gcol.inputs["Fac"])
c.link(nt, gcol.outputs["Color"], bsdf.inputs["Base Color"])
gb = c.node(nt, "ShaderNodeBump", Strength=0.5)
c.link(nt, swirl.outputs["Fac"], gb.inputs["Height"])
c.link(nt, gb.outputs[0], bsdf.inputs["Normal"])
ground = c.primitive("plane", "ground", ground_mat, size=200)

# Mist banks on the right: big soft lumps of glowing red haze.
mist = bpy.data.materials.new("mist")
mist.use_nodes = True
mnt = mist.node_tree
mnt.nodes.clear()
out = c.node(mnt, "ShaderNodeOutputMaterial")
vol = c.node(mnt, "ShaderNodeVolumePrincipled", Density=0.12)
vol.inputs["Color"].default_value = (*c.srgb(230, 60, 50), 1)
c.link(mnt, vol.outputs[0], out.inputs["Volume"])
# Wisps: the density follows twisted noise, so the banks curl like the original's swirls.
mtc = c.node(mnt, "ShaderNodeTexCoord")
wisp = c.node(mnt, "ShaderNodeTexNoise", Scale=1.2, Detail=6.0, Distortion=3.0)
c.link(mnt, mtc.outputs["Object"], wisp.inputs["Vector"])
dens = c.node(mnt, "ShaderNodeMapRange", **{"From Min": 0.45, "From Max": 0.7, "To Min": 0.0, "To Max": 0.9})
c.link(mnt, wisp.outputs["Fac"], dens.inputs["Value"])
c.link(mnt, dens.outputs[0], vol.inputs["Density"])
for i in range(8):
    m = c.primitive("ico_sphere", f"mist{i}", mist, subdivisions=3, radius=random.uniform(1.2, 2.4))
    m.location = (random.uniform(2, 9), random.uniform(1, 8), random.uniform(0.0, 0.6))
    m.scale = (2.2, 1.4, 0.7)

# The emplacement: a game turret, scaled up to a heavy gun.
gun = c.model("newshg-201", location=(-1.6, 1.6, 0.45), rotation=(0, 0, -50), scale=1.3)

# The figure at its controls, built from capsules: legs braced, arms on the gun.
suit = c.material("suit", c.srgb(90, 80, 80), metallic=0.3, roughness=0.5)


def limb(name, a, b, r):
    a, b = c.Vector(a), c.Vector(b)
    o = c.primitive("cylinder", name, suit, vertices=16, radius=r, depth=(b - a).length)
    o.location = (a + b) / 2
    c.aim_z(o, b - a)
    for end in (a, b):
        j = c.primitive("uv_sphere", f"{name}_joint", suit, segments=16, ring_count=8, radius=r)
        j.location = end
        c.smooth(j)
    c.smooth(o)
    return o


X, Y = -3.6, 1.2
limb("leg_l", (X - 0.15, Y, 0.05), (X - 0.05, Y + 0.05, 0.85), 0.11)
limb("leg_r", (X + 0.35, Y + 0.1, 0.05), (X + 0.15, Y + 0.05, 0.85), 0.11)
limb("torso", (X + 0.05, Y + 0.05, 0.9), (X + 0.35, Y + 0.1, 1.55), 0.2)
limb("arm_l", (X + 0.3, Y, 1.5), (X + 0.85, Y + 0.15, 1.15), 0.07)
limb("arm_r", (X + 0.4, Y + 0.2, 1.5), (X + 0.95, Y + 0.35, 1.2), 0.07)
head = c.primitive("uv_sphere", "head", suit, segments=24, ring_count=12, radius=0.17)
head.location = (X + 0.45, Y + 0.12, 1.78)
c.smooth(head)
pack = c.primitive("cube", "pack", suit, size=0.35)
pack.location = (X - 0.05, Y + 0.12, 1.3)
pack.rotation_euler = (0, math.radians(-25), 0)

# Red light: a hard key from the top left, a glow from below the mist.
c.light("SUN", (-6, -4, 6), (0, 2, 0), energy=4.0, color=RED, angle=2)
c.light("AREA", (6, 2, 3), (0, 2, 0.5), energy=400, color=c.srgb(255, 90, 60), size=6)

cam = c.camera((-0.5, -6.5, 5.6), (-0.5, 1.5, 3.6), lens=30)
bpy.context.view_layer.update()

# The holo-screen: a grid panel just in front of the camera, over the top two thirds of the frame,
# with a glowing edge along its bottom.
grid_mat = bpy.data.materials.new("grid")
grid_mat.use_nodes = True
nt = grid_mat.node_tree
nt.nodes.clear()
out = c.node(nt, "ShaderNodeOutputMaterial")
tc = c.node(nt, "ShaderNodeTexCoord")
mp = c.node(nt, "ShaderNodeMapping")
mp.inputs["Scale"].default_value = (40, 17, 1)  # square cells on the 8:3.3 panel
c.link(nt, tc.outputs["UV"], mp.inputs["Vector"])
brick = c.node(nt, "ShaderNodeTexBrick", Scale=1.0, **{"Mortar Size": 0.05, "Mortar Smooth": 0.4, "Bias": 0.0,
                                                    "Brick Width": 1.0, "Row Height": 1.0})
brick.offset = 0.0
brick.inputs["Color1"].default_value = (*c.srgb(60, 4, 6), 1)
brick.inputs["Color2"].default_value = (*c.srgb(54, 4, 6), 1)
brick.inputs["Mortar"].default_value = (*c.srgb(150, 20, 20), 1)
c.link(nt, mp.outputs[0], brick.inputs["Vector"])
# Darker toward the top, as the original's.
sep = c.node(nt, "ShaderNodeSeparateXYZ")
c.link(nt, tc.outputs["UV"], sep.inputs[0])
fade = c.node(nt, "ShaderNodeMapRange", **{"From Min": 0.0, "From Max": 1.0, "To Min": 1.0, "To Max": 0.55})
c.link(nt, sep.outputs["Y"], fade.inputs["Value"])
em = c.node(nt, "ShaderNodeEmission")
c.link(nt, brick.outputs["Color"], em.inputs["Color"])
c.link(nt, fade.outputs[0], em.inputs["Strength"])
c.link(nt, em.outputs[0], out.inputs["Surface"])

D = 1.0  # distance in front of the camera
right, up, view = c.camera_axes(cam)
half_w = D * 18 / cam.data.lens  # half the frame's width at D (36 mm sensor width)
half_h = half_w * c.HEIGHT / c.WIDTH
panel_h = half_h * 2 * 0.66
screen = c.primitive("plane", "screen", grid_mat, size=1.0)
screen.scale = (half_w * 2, panel_h, 1)
screen.location = cam.location + view * D + up * (half_h - panel_h / 2)
screen.rotation_euler = cam.rotation_euler
edge = c.primitive("plane", "edge", c.emission("edge", c.srgb(255, 60, 50), 3.0), size=1.0)
edge.scale = (half_w * 2, panel_h * 0.006, 1)
edge.location = screen.location - up * (panel_h / 2) - view * 0.001
edge.rotation_euler = cam.rotation_euler

c.save(NAME)
