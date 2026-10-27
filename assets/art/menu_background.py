"""Picture 2: the menu background (title-screen submenus: episode, difficulty, setup, high
scores, the network wait screen; JE_loadPic 2 in mainint.c, menus.c, opentyr.c).

A red sun boiling with flares on its upper limb, its lower half in shadow, hung in front of a
blue wireframe grid that recedes across the frame. The lower half stays dark for the menu text.
The original's credit line along the bottom is left out. Writes public/art/menu_background.webp.
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as c  # noqa: E402

NAME = "menu_background"
bpy = c.bpy

c.new_scene(samples=96)

# The grid: a big plane of thin glowing lines, tilted so it recedes up and to the right.
grid_mat = bpy.data.materials.new("grid")
grid_mat.use_nodes = True
nt = grid_mat.node_tree
nt.nodes.clear()
out = c.node(nt, "ShaderNodeOutputMaterial")
tc = c.node(nt, "ShaderNodeTexCoord")
mapping = c.node(nt, "ShaderNodeMapping")
mapping.inputs["Scale"].default_value = (0.5, 0.5, 0.5)  # 2-unit cells
c.link(nt, tc.outputs["Object"], mapping.inputs["Vector"])
# Lines: |fract(x) - 0.5| close to 0.5 on either axis; a brick texture with mortar does exactly that.
brick = c.node(nt, "ShaderNodeTexBrick", Scale=1.0, **{"Mortar Size": 0.022, "Mortar Smooth": 0.7, "Bias": 0.0,
                                                    "Brick Width": 1.0, "Row Height": 1.0})
brick.offset = 0.0
brick.squash = 1.0
brick.inputs["Color1"].default_value = (0, 0, 0, 1)
brick.inputs["Color2"].default_value = (0, 0, 0, 1)
brick.inputs["Mortar"].default_value = (1, 1, 1, 1)
c.link(nt, mapping.outputs[0], brick.inputs["Vector"])
# Fade the grid with distance from the camera so it dissolves into the dark.
cam_dist = c.node(nt, "ShaderNodeCameraData")
fade = c.node(nt, "ShaderNodeMapRange", **{"From Min": 10.0, "From Max": 70.0, "To Min": 0.55, "To Max": 0.03})
c.link(nt, cam_dist.outputs["View Distance"], fade.inputs["Value"])
glow = c.node(nt, "ShaderNodeMath", p_operation="MULTIPLY")
c.link(nt, brick.outputs["Fac"], glow.inputs[0])
c.link(nt, fade.outputs[0], glow.inputs[1])
em = c.node(nt, "ShaderNodeEmission")
em.inputs["Color"].default_value = (*c.srgb(60, 130, 210), 1)
c.link(nt, glow.outputs[0], em.inputs["Strength"])
mixs = c.node(nt, "ShaderNodeMixShader")
transp = c.node(nt, "ShaderNodeBsdfTransparent")
c.link(nt, brick.outputs["Fac"], mixs.inputs["Fac"])
c.link(nt, transp.outputs[0], mixs.inputs[1])
c.link(nt, em.outputs[0], mixs.inputs[2])
c.link(nt, mixs.outputs[0], out.inputs["Surface"])

grid = c.primitive("plane", "grid", grid_mat, size=160)
grid.location = (0, 30, -2)
grid.rotation_euler = (math.radians(68), math.radians(-18), math.radians(22))

# Tiny dust of stars between the grid lines.
wnt = bpy.context.scene.world.node_tree
bg = next(n for n in wnt.nodes if n.type == "BACKGROUND")
coord = c.node(wnt, "ShaderNodeTexCoord")
stars = c.starfield(wnt, coord.outputs["Generated"], scale=700, density=0.01, strength=0.5)
c.link(wnt, stars.outputs[0], bg.inputs["Color"])

# The sun: churning red plasma, bright where it faces up (its lit limb), black below.
sun_mat = bpy.data.materials.new("sun")
sun_mat.use_nodes = True
nt = sun_mat.node_tree
nt.nodes.clear()
out = c.node(nt, "ShaderNodeOutputMaterial")
tc = c.node(nt, "ShaderNodeTexCoord")
noise = c.node(nt, "ShaderNodeTexNoise", Scale=1.8, Detail=12.0, Roughness=0.6, Distortion=0.5)
c.link(nt, tc.outputs["Object"], noise.inputs["Vector"])
plasma = c.ramp(nt, [
    (0.30, c.srgb(6, 0, 0)),
    (0.46, c.srgb(60, 8, 4)),
    (0.58, c.srgb(140, 34, 12)),
    (0.72, c.srgb(230, 96, 44)),
])
c.link(nt, noise.outputs["Fac"], plasma.inputs["Fac"])
geo = c.node(nt, "ShaderNodeNewGeometry")
# Light falls on the top, a little from the left: the normal along that direction.
toward = c.node(nt, "ShaderNodeVectorMath", p_operation="DOT_PRODUCT")
toward.inputs[1].default_value = (-0.35, -0.2, 0.92)
c.link(nt, geo.outputs["Normal"], toward.inputs[0])
lit = c.node(nt, "ShaderNodeMapRange", **{"From Min": -0.05, "From Max": 0.9, "To Min": 0.0, "To Max": 1.0})
lit.interpolation_type = "SMOOTHSTEP"
c.link(nt, toward.outputs["Value"], lit.inputs["Value"])
strength = c.node(nt, "ShaderNodeMath", p_operation="MULTIPLY", values={1: 2.4})
c.link(nt, lit.outputs[0], strength.inputs[0])
em = c.node(nt, "ShaderNodeEmission")
c.link(nt, plasma.outputs["Color"], em.inputs["Color"])
c.link(nt, strength.outputs[0], em.inputs["Strength"])
c.link(nt, em.outputs[0], out.inputs["Surface"])

sun = c.primitive("uv_sphere", "sun", sun_mat, segments=128, ring_count=64, radius=3.0)
c.smooth(sun)
sun.location = (0, 0, 0.6)

# Flares: lumpy plasma blobs rising off the upper limb (displaced, subdivided icospheres).
flare_mat = bpy.data.materials.new("flare")
flare_mat.use_nodes = True
nt = flare_mat.node_tree
nt.nodes.clear()
out = c.node(nt, "ShaderNodeOutputMaterial")
tc = c.node(nt, "ShaderNodeTexCoord")
noise = c.node(nt, "ShaderNodeTexNoise", Scale=2.5, Detail=6.0, Roughness=0.5, Distortion=0.3)
c.link(nt, tc.outputs["Object"], noise.inputs["Vector"])
fcol = c.ramp(nt, [(0.3, c.srgb(50, 6, 2)), (0.55, c.srgb(150, 40, 14)), (0.75, c.srgb(230, 110, 60))])
c.link(nt, noise.outputs["Fac"], fcol.inputs["Fac"])
em = c.node(nt, "ShaderNodeEmission", Strength=1.5)
c.link(nt, fcol.outputs["Color"], em.inputs["Color"])
c.link(nt, em.outputs[0], out.inputs["Surface"])

tex = bpy.data.textures.new("lumps", "CLOUDS")
tex.noise_scale = 0.45
for i, (ang, size, lift) in enumerate([(140, 0.55, 0.05), (42, 0.6, 0.15), (122, 0.32, -0.1)]):
    a = math.radians(ang)
    blob = c.primitive("ico_sphere", f"flare{i}", flare_mat, subdivisions=5, radius=size)
    r = 3.0 + lift
    blob.location = (math.cos(a) * r, -0.6, 0.6 + math.sin(a) * r)
    d = blob.modifiers.new("lumps", "DISPLACE")
    d.texture = tex
    d.strength = size * 0.6
    d.texture_coords = "OBJECT"
    c.smooth(blob)

c.camera((0, -14, 0.6), (0, 0, 0.6), lens=40)
c.save(NAME)
