"""Picture 12: the second intro card (`intro_logos`, mainint.c), the developer's logo.

The original shows a blazing sun eclipsed by a dark sphere, the light bursting through billows of
smoke, in front of a fine grid fading into black, with the studio's name in bevelled gold below.
The name and the figure in the smoke are the studio's own, so this keeps the eclipse, the smoke
and the grid, and leaves the band under it empty. Writes public/art/intro_studio.webp.
"""

import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as c  # noqa: E402

NAME = "intro_studio"
bpy = c.bpy
random.seed(12)

c.new_scene(samples=192)
bpy.context.scene.cycles.volume_bounces = 2

# The grid: fine gold lines on a backdrop, brightest around the eclipse and gone at the corners.
grid = bpy.data.materials.new("grid")
grid.use_nodes = True
nt = grid.node_tree
nt.nodes.clear()
out = c.node(nt, "ShaderNodeOutputMaterial")
tc = c.node(nt, "ShaderNodeTexCoord")
brick = c.node(nt, "ShaderNodeTexBrick", Scale=1.0, **{"Mortar Size": 0.04, "Mortar Smooth": 0.5, "Bias": 0.0,
                                                    "Brick Width": 1.0, "Row Height": 1.0})
brick.offset = 0.0
brick.inputs["Color1"].default_value = (0, 0, 0, 1)
brick.inputs["Color2"].default_value = (0, 0, 0, 1)
brick.inputs["Mortar"].default_value = (1, 1, 1, 1)
c.link(nt, tc.outputs["Object"], brick.inputs["Vector"])
dist = c.node(nt, "ShaderNodeVectorMath", p_operation="LENGTH")
c.link(nt, tc.outputs["Object"], dist.inputs[0])
vign = c.node(nt, "ShaderNodeMapRange", **{"From Min": 2.0, "From Max": 13.0, "To Min": 0.32, "To Max": 0.0})
c.link(nt, dist.outputs["Value"], vign.inputs["Value"])
lines = c.node(nt, "ShaderNodeMath", p_operation="MULTIPLY")
c.link(nt, brick.outputs["Fac"], lines.inputs[0])
c.link(nt, vign.outputs[0], lines.inputs[1])
em = c.node(nt, "ShaderNodeEmission")
em.inputs["Color"].default_value = (*c.srgb(200, 170, 120), 1)
c.link(nt, lines.outputs[0], em.inputs["Strength"])
c.link(nt, em.outputs[0], out.inputs["Surface"])
backdrop = c.primitive("plane", "grid", grid, size=80)
backdrop.location = (-1.5, 14, 2.2)
backdrop.rotation_euler = (math.radians(90), 0, 0)

# The sun: white-hot, behind and to the upper left of the dark body that eclipses it.
sun = c.primitive("uv_sphere", "sun", c.emission("sun", c.srgb(255, 244, 220), 30.0), segments=64, ring_count=32, radius=2.0)
sun.location = (-3.0, 6.0, 2.4)
c.light("POINT", (-3.0, 4.5, 2.4), energy=9000, color=c.srgb(255, 236, 200), size=1.8)

body = c.primitive("uv_sphere", "eclipse", c.material("black", (0.0, 0.0, 0.0), roughness=0.9), segments=64, ring_count=32, radius=1.75)
body.location = (-1.8, 2.0, 1.0)
c.smooth(body)

# Smoke: billows of grey-white volume around the light, thicker to the right where the original's
# figure stood.
smoke = bpy.data.materials.new("smoke")
smoke.use_nodes = True
nt = smoke.node_tree
nt.nodes.clear()
out = c.node(nt, "ShaderNodeOutputMaterial")
tc = c.node(nt, "ShaderNodeTexCoord")
noise = c.node(nt, "ShaderNodeTexNoise", Scale=0.55, Detail=10.0, Roughness=0.6, Distortion=0.8)
c.link(nt, tc.outputs["Object"], noise.inputs["Vector"])
dens = c.node(nt, "ShaderNodeMapRange", **{"From Min": 0.5, "From Max": 0.75, "To Min": 0.0, "To Max": 1.6})
c.link(nt, noise.outputs["Fac"], dens.inputs["Value"])
# Fade to nothing at the edge of each puff (object-space distance), so no box shows.
d = c.node(nt, "ShaderNodeVectorMath", p_operation="LENGTH")
c.link(nt, tc.outputs["Object"], d.inputs[0])
edge = c.node(nt, "ShaderNodeMapRange", **{"From Min": 0.55, "From Max": 1.0, "To Min": 1.0, "To Max": 0.0})
c.link(nt, d.outputs["Value"], edge.inputs["Value"])
dmul = c.node(nt, "ShaderNodeMath", p_operation="MULTIPLY")
c.link(nt, dens.outputs[0], dmul.inputs[0])
c.link(nt, edge.outputs[0], dmul.inputs[1])
vol = c.node(nt, "ShaderNodeVolumePrincipled")
vol.inputs["Color"].default_value = (*c.srgb(220, 214, 205), 1)
c.link(nt, dmul.outputs[0], vol.inputs["Density"])
c.link(nt, vol.outputs[0], out.inputs["Volume"])
for i, (x, z, r) in enumerate([(-4.4, 3.4, 2.6), (-1.6, 4.2, 2.6), (1.0, 3.4, 2.8), (3.2, 2.0, 2.6),
                               (-4.6, 0.8, 2.0), (2.8, 5.0, 2.0), (-0.6, 1.0, 2.0), (5.2, 3.6, 2.2)]):
    puff = c.primitive("cube", f"smoke{i}", smoke, size=2.0)
    puff.location = (x, 4.0 + random.uniform(-1, 1), z)
    puff.scale = (r, r * 0.8, r * 0.8)
    puff.rotation_euler = (random.uniform(0, 3), random.uniform(0, 3), random.uniform(0, 3))

c.camera((0, -14, 0.6), (0, 4, 1.4), lens=34)
c.save(NAME)
