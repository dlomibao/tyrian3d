"""Picture 0: episode 4's special ending, under "ENGAGE!!!" (`]P 000` shows tshp2.pcx, a file of its
own rather than a tyrian.pic picture; levels4.dat section 41).

The incredible ship you found blasts off through a golden haze, engines flaring, the towers of a
city fading behind it. The ship is the Nort ship (ship-nort-ship) in gold, seen from the side
and a little below. Writes public/art/story_engage.webp.
"""

import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as c  # noqa: E402

NAME = "story_engage"
bpy = c.bpy
random.seed(41)

c.new_scene(samples=160)
bpy.context.scene.cycles.volume_bounces = 1
c.world_color(c.srgb(150, 140, 190), 0.9)

# The haze: a golden volume over everything, thicker with distance.
haze = bpy.data.materials.new("haze")
haze.use_nodes = True
nt = haze.node_tree
nt.nodes.clear()
out = c.node(nt, "ShaderNodeOutputMaterial")
vol = c.node(nt, "ShaderNodeVolumePrincipled", Density=0.03, Anisotropy=0.4)
vol.inputs["Color"].default_value = (*c.srgb(240, 210, 160), 1)
c.link(nt, vol.outputs[0], out.inputs["Volume"])
fog = c.primitive("cube", "haze", haze, size=1.0)
fog.scale = (200, 120, 70)
fog.location = (0, 68, 10)  # from just behind the ship back past the city

# The city: towers of every height fading into the haze behind the ship.
tower = c.material("tower", c.srgb(170, 150, 160), metallic=0.3, roughness=0.6)
for i in range(70):
    w = random.uniform(2, 6)
    h = random.uniform(15, 60)
    t = c.primitive("cube", f"tower{i}", tower, size=1.0)
    t.scale = (w, w, h)
    t.location = (random.uniform(-70, 70), random.uniform(40, 100), h / 2 - 12)

# Ground: dusty, dark at the bottom of the frame.
c.primitive("plane", "ground", c.material("ground", c.srgb(90, 80, 70), roughness=0.9), size=400).location = (0, 0, -12)

# The ship, in gold, nose to the right and climbing.
ship = c.model("ship-nort-ship", scale=6.0)
c.aim(ship, (1.0, -0.3, 0.22), (-0.15, -0.45, 1.0))
gold = c.material("gold", c.srgb(220, 170, 90), metallic=1.0, roughness=0.25)
for o in ship.children_recursive:
    if o.type == "MESH":
        for slot in o.material_slots:
            if slot.material and not slot.material.name.startswith("engine"):
                b = next(n for n in slot.material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
                col = b.inputs["Base Color"].default_value
                lum = 0.3 * col[0] + 0.6 * col[1] + 0.1 * col[2]
                b.inputs["Base Color"].default_value = (0.75 + lum, 0.52 + lum * 0.8, 0.22 + lum * 0.4, 1)
                b.inputs["Metallic"].default_value = 1.0
                b.inputs["Roughness"].default_value = 0.28

# Engine blast: glowing gas streaming back from the tail (emissive volumes in cones), hottest at
# the nozzles and torn up by turbulence toward the ends, with a hot light among them.
flame = bpy.data.materials.new("flame")
flame.use_nodes = True
nt = flame.node_tree
nt.nodes.clear()
out = c.node(nt, "ShaderNodeOutputMaterial")
tc = c.node(nt, "ShaderNodeTexCoord")
sep = c.node(nt, "ShaderNodeSeparateXYZ")
c.link(nt, tc.outputs["Generated"], sep.inputs[0])
fcol = c.ramp(nt, [(0.0, c.srgb(255, 250, 225)), (0.35, c.srgb(255, 200, 80)), (1.0, c.srgb(230, 90, 20))])
c.link(nt, sep.outputs["Z"], fcol.inputs["Fac"])
turb = c.node(nt, "ShaderNodeTexNoise", Scale=2.5, Detail=8.0, Distortion=1.2)
c.link(nt, tc.outputs["Object"], turb.inputs["Vector"])
fade = c.node(nt, "ShaderNodeMapRange", **{"From Min": 0.0, "From Max": 1.0, "To Min": 60.0, "To Max": 0.0})
c.link(nt, sep.outputs["Z"], fade.inputs["Value"])
ragged = c.node(nt, "ShaderNodeMapRange", **{"From Min": 0.35, "From Max": 0.7, "To Min": 0.0, "To Max": 1.0})
c.link(nt, turb.outputs["Fac"], ragged.inputs["Value"])
glow = c.node(nt, "ShaderNodeMath", p_operation="MULTIPLY")
c.link(nt, fade.outputs[0], glow.inputs[0])
c.link(nt, ragged.outputs[0], glow.inputs[1])
vol = c.node(nt, "ShaderNodeVolumePrincipled", Density=0.0)
c.link(nt, fcol.outputs["Color"], vol.inputs["Emission Color"])
c.link(nt, glow.outputs[0], vol.inputs["Emission Strength"])
c.link(nt, vol.outputs[0], out.inputs["Volume"])
bpy.context.view_layer.update()
tail = ship.matrix_world @ c.Vector((0, -1.0, 0))
back = (ship.matrix_world.to_3x3() @ c.Vector((0, -1, 0))).normalized()
for i, (dx, dz, r, length) in enumerate([(0, 0, 1.0, 10), (-1.2, -0.4, 0.7, 7), (1.2, -0.3, 0.7, 8)]):
    f = c.primitive("cone", f"flame{i}", flame, vertices=32, radius1=r, radius2=r * 2.2, depth=length)
    f.data.transform(c.Matrix.Translation((0, 0, length / 2)))
    f.location = tail + c.Vector((dx, 0, dz))
    c.aim_z(f, back + c.Vector((0, 0, -0.25)))
c.light("POINT", tail + back * 3, energy=6000, color=c.srgb(255, 180, 80), size=3)

# Low, warm sun from the left; violet sky light from above.
c.light("SUN", (-10, -6, 3), (0, 0, 0), energy=4.0, color=c.srgb(255, 220, 170), angle=4)

c.camera((-6, -24, -4.0), (0.5, 0, 0.8), lens=40)
c.save(NAME)
