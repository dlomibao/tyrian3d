"""Picture 7: the end of episode 2 (`]P 007`, levels2.dat section 13), under the text about blasting
your way to freedom with an invasion at hand.

A dragon's head lying dead on a floor of grey stone tiles, snout to the left, a cluster of green
crystal grown out of the wound behind its eye, its neck running off to the right. The head is the
Gryphon level's dragon (newsh0-119), the crystal the green gems (tyrian10-32).
Writes public/art/story_dragon.webp.
"""

import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as c  # noqa: E402

NAME = "story_dragon"
bpy = c.bpy
random.seed(7)

c.new_scene(samples=160)

# The floor: big worn slabs of streaked grey stone with dark joints.
stone = bpy.data.materials.new("stone")
stone.use_nodes = True
nt = stone.node_tree
bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
bsdf.inputs["Roughness"].default_value = 0.75
tc = c.node(nt, "ShaderNodeTexCoord")
brick = c.node(nt, "ShaderNodeTexBrick", Scale=0.28, **{"Mortar Size": 0.005, "Mortar Smooth": 0.5,
                                                     "Brick Width": 1.0, "Row Height": 1.0})
brick.offset = 0.0
brick.inputs["Color1"].default_value = (1, 1, 1, 1)
brick.inputs["Color2"].default_value = (0.8, 0.8, 0.8, 1)
brick.inputs["Mortar"].default_value = (0, 0, 0, 1)
c.link(nt, tc.outputs["Object"], brick.inputs["Vector"])
streak_map = c.node(nt, "ShaderNodeMapping")
streak_map.inputs["Scale"].default_value = (0.6, 1.4, 1.0)
c.link(nt, tc.outputs["Object"], streak_map.inputs["Vector"])
streaks = c.node(nt, "ShaderNodeTexNoise", Scale=2.0, Detail=12.0, Roughness=0.65, Distortion=0.6)
c.link(nt, streak_map.outputs[0], streaks.inputs["Vector"])
scol = c.ramp(nt, [(0.3, c.srgb(48, 50, 54)), (0.5, c.srgb(90, 92, 96)), (0.75, c.srgb(140, 142, 146))])
c.link(nt, streaks.outputs["Fac"], scol.inputs["Fac"])
tint = c.node(nt, "ShaderNodeMix", p_data_type="RGBA", p_blend_type="MULTIPLY", Factor=1.0)
c.link(nt, scol.outputs["Color"], tint.inputs[6])
c.link(nt, brick.outputs["Color"], tint.inputs[7])
c.link(nt, tint.outputs[2], bsdf.inputs["Base Color"])
bump = c.node(nt, "ShaderNodeBump", Strength=0.6, Distance=0.02)
c.link(nt, brick.outputs["Fac"], bump.inputs["Height"])
c.link(nt, bump.outputs[0], bsdf.inputs["Normal"])
floor = c.primitive("plane", "floor", stone, size=60)
floor.rotation_euler = (0, 0, math.radians(-12))

# The dragon's head, lying on the floor, snout to the left, tipped a little onto its side. Enemy
# models face down the screen (-Y), toward the player, so +Y (the back of the head) points right.
head = c.model("newsh0-119", location=(-0.4, 0.2, 0.35), scale=1.0)
c.aim(head, (1.0, 0.15, -0.02), (0.15, -0.2, 1.0))
c.tint_model(head, roughness=0.45, glow=0.0)

# Its neck: a scaly, tapering tube from behind the head off the right of the frame.
scales = bpy.data.materials.new("scales")
scales.use_nodes = True
nt = scales.node_tree
bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
bsdf.inputs["Roughness"].default_value = 0.45
tc = c.node(nt, "ShaderNodeTexCoord")
vor = c.node(nt, "ShaderNodeTexVoronoi", Scale=9.0)
c.link(nt, tc.outputs["Object"], vor.inputs["Vector"])
ncol = c.ramp(nt, [(0.0, c.srgb(60, 110, 150)), (0.5, c.srgb(30, 62, 92)), (1.0, c.srgb(10, 22, 36))])
c.link(nt, vor.outputs["Distance"], ncol.inputs["Fac"])
c.link(nt, ncol.outputs["Color"], bsdf.inputs["Base Color"])
nb = c.node(nt, "ShaderNodeBump", Strength=0.8, Distance=0.05)
c.link(nt, vor.outputs["Distance"], nb.inputs["Height"])
c.link(nt, nb.outputs[0], bsdf.inputs["Normal"])

curve = bpy.data.curves.new("neck", "CURVE")
curve.dimensions = "3D"
curve.bevel_depth = 0.42
curve.bevel_resolution = 6
curve.use_fill_caps = True
spline = curve.splines.new("BEZIER")
pts = [(0.9, 0.4, 0.38), (2.4, 0.9, 0.45), (4.2, 0.3, 0.5), (6.5, 1.0, 0.55)]
spline.bezier_points.add(len(pts) - 1)
for bp, p in zip(spline.bezier_points, pts):
    bp.co = p
    bp.handle_left_type = bp.handle_right_type = "AUTO"
for bp, r in zip(spline.bezier_points, (0.7, 1.0, 1.15, 1.25)):
    bp.radius = r
neck = bpy.data.objects.new("neck", curve)
bpy.context.scene.collection.objects.link(neck)
curve.materials.append(scales)

# Torn armour plating over the neck, the colour of the original's cloth.
plate = c.material("plate", c.srgb(70, 84, 88), metallic=0.7, roughness=0.35)
for i in range(5):
    p = c.primitive("cube", f"plate{i}", plate, size=1.0)
    p.scale = (0.5, 0.75, 0.06)
    p.location = (3.2 + i * 0.75, 0.6 + random.uniform(-0.25, 0.3), 1.15 + random.uniform(-0.1, 0.15))
    p.rotation_euler = (math.radians(random.uniform(-25, 25)), math.radians(random.uniform(-30, 10)), math.radians(random.uniform(-20, 20)))
    bev = p.modifiers.new("bevel", "BEVEL")
    bev.width = 0.03

# The crystal: green shards bursting out of the wound behind the eye, a few of the green gems
# (tyrian10-32) caught among them.
crystal = c.material("crystal", c.srgb(40, 170, 60), roughness=0.08, emission=c.srgb(40, 200, 70), emission_strength=0.6)
wound = c.Vector((0.15, 0.3, 0.55))
for i in range(16):
    length = random.uniform(0.35, 0.8)
    shard = c.primitive("cone", f"shard{i}", crystal, vertices=6, radius1=random.uniform(0.06, 0.13), radius2=0.0, depth=length)
    shard.data.transform(c.Matrix.Translation((0, 0, length / 2)))
    shard.location = wound + c.Vector((random.uniform(-0.2, 0.2), random.uniform(-0.2, 0.2), 0))
    c.aim_z(shard, (random.uniform(-0.6, 0.8), random.uniform(-0.9, 0.5), random.uniform(0.4, 1.0)), random.uniform(0, 6.3))
for i in range(3):
    g = c.model("tyrian10-32", scale=random.uniform(0.22, 0.3))
    g.location = wound + c.Vector((random.uniform(-0.3, 0.3), random.uniform(-0.3, 0.1), 0.12))
    g.rotation_euler = (random.uniform(-0.8, 0.8), random.uniform(-0.8, 0.8), random.uniform(0, 6.3))
c.light("POINT", (0.15, 0.0, 1.2), energy=20, color=c.srgb(90, 255, 110), size=0.3)

# Grey daylight from the top left, a cooler bounce from the right.
c.light("SUN", (-6, -4, 9), (0, 0, 0), energy=3.0, color=c.srgb(255, 248, 235), angle=6)
c.light("AREA", (5, -4, 4), (0, 0, 0), energy=150, color=c.srgb(180, 200, 255), size=4)
c.world_color(c.srgb(40, 42, 48), 0.6)

c.camera((0.0, -3.5, 3.6), (0.5, 0.35, 0.25), lens=40)
c.save(NAME)
