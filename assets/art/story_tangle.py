"""Picture 9: the end of episode 1 and the news reports after it (`]P 009`, levels1.dat section 42).

A dim brown thicket of horns, claws and tendrils sprawling across the dark, one jagged spine
standing up in the middle, lit from above so only its ridges catch the light. The text runs over
it, so it stays dark. Writes public/art/story_tangle.webp.
"""

import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as c  # noqa: E402

NAME = "story_tangle"
bpy = c.bpy
random.seed(9)

c.new_scene(samples=128)

# Chitin: dark brown, glossy on the ridges, with fine streaks along each horn.
chitin = bpy.data.materials.new("chitin")
chitin.use_nodes = True
nt = chitin.node_tree
bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
bsdf.inputs["Roughness"].default_value = 0.32
tc = c.node(nt, "ShaderNodeTexCoord")
noise = c.node(nt, "ShaderNodeTexNoise", Scale=5.0, Detail=10.0, Roughness=0.6, Distortion=0.8)
c.link(nt, tc.outputs["Object"], noise.inputs["Vector"])
col = c.ramp(nt, [(0.3, c.srgb(26, 14, 8)), (0.55, c.srgb(84, 50, 30)), (0.75, c.srgb(140, 96, 64))])
c.link(nt, noise.outputs["Fac"], col.inputs["Fac"])
c.link(nt, col.outputs["Color"], bsdf.inputs["Base Color"])
bump = c.node(nt, "ShaderNodeBump", Strength=0.5)
c.link(nt, noise.outputs["Fac"], bump.inputs["Height"])
c.link(nt, bump.outputs[0], bsdf.inputs["Normal"])


def horn(name, base, direction, length, radius, bend):
    """A tapered horn from `base` along `direction`, curling by `bend` degrees."""
    h = c.primitive("cone", name, chitin, vertices=24, radius1=radius, radius2=0.0, depth=length)
    # The cone runs along +Z from its middle; move it so it grows from its base.
    h.data.transform(c.Matrix.Translation((0, 0, length / 2)))
    sub = h.modifiers.new("loops", "SUBSURF")
    sub.levels = sub.render_levels = 2
    sub.subdivision_type = "SIMPLE"
    d = h.modifiers.new("bend", "SIMPLE_DEFORM")
    d.deform_method = "BEND"
    d.angle = math.radians(bend)
    d.deform_axis = "Y"
    c.smooth(h)
    h.location = base
    c.aim_z(h, direction, random.uniform(0, 2 * math.pi))
    return h


# A knotted core, wider than tall.
core = c.primitive("ico_sphere", "core", chitin, subdivisions=5, radius=1.0)
core.scale = (2.8, 1.2, 1.3)
tex = bpy.data.textures.new("knots", "VORONOI")
tex.noise_scale = 0.45
disp = core.modifiers.new("knots", "DISPLACE")
disp.texture = tex
disp.strength = 0.6
c.smooth(core)

# Horns and claws fanning out sideways and up, longer toward the edges.
for i in range(130):
    a = random.uniform(-math.pi * 0.95, math.pi * 0.95)
    up = random.uniform(-0.25, 1.0)
    direction = (math.sin(a) * 1.4, random.uniform(-0.4, 0.2), up + abs(math.cos(a)) * 0.6)
    base = (math.sin(a) * random.uniform(0.5, 2.6), random.uniform(-0.6, 0.6), random.uniform(-0.6, 0.8))
    length = random.uniform(1.2, 3.2) * (1.0 + 0.35 * abs(math.sin(a)))
    horn(f"horn{i}", base, direction, length, random.uniform(0.1, 0.3), random.uniform(-110, 110))

# The spine standing up in the middle: a ridged column with hooked teeth up both sides.
column = horn("column", (0.0, 0.0, 0.3), (0.05, 0.0, 1.0), 4.4, 0.42, 8)
rings = column.modifiers.new("ridges", "DISPLACE")
rings.texture = bpy.data.textures.new("ridges", "WOOD")
rings.texture.wood_type = "RINGS"
rings.texture.noise_basis_2 = "SAW"
rings.texture.turbulence = 0.0
rings.texture_coords = "OBJECT"
rings.strength = 0.08
for i in range(12):
    t = i / 11
    side = 1 if i % 2 else -1
    horn(f"tooth{i}", (side * (0.32 - 0.25 * t), 0.0, 0.8 + t * 3.2), (side * 0.9, -0.3, 0.6), 0.55 - 0.3 * t, 0.09, side * 50)

# Tendrils trailing underneath.
for i in range(22):
    curve = bpy.data.curves.new(f"tendril{i}", "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = random.uniform(0.04, 0.1)
    curve.bevel_resolution = 3
    spline = curve.splines.new("BEZIER")
    spline.bezier_points.add(3)
    x0 = random.uniform(-2.5, 2.5)
    p = (x0, random.uniform(-0.4, 0.4), random.uniform(-0.6, 0.2))
    for bp in spline.bezier_points:
        bp.co = p
        bp.handle_left_type = bp.handle_right_type = "AUTO"
        p = (p[0] + random.uniform(-1.2, 1.2) + math.copysign(0.4, x0), p[1] + random.uniform(-0.4, 0.4), p[2] - random.uniform(0.3, 1.0))
    spline.bezier_points[-1].radius = 0.1
    obj = bpy.data.objects.new(f"tendril{i}", curve)
    bpy.context.scene.collection.objects.link(obj)
    curve.materials.append(chitin)

# Light from above and a little behind: ridges and tips glint, hollows stay black.
c.light("AREA", (0, 2.5, 7), (0, 0, 0.5), energy=1400, color=c.srgb(255, 214, 170), size=5)
c.light("SPOT", (-4, -7, 3), (0, 0, 0.5), energy=500, color=c.srgb(255, 160, 110), size=1)

c.camera((0, -11.5, 2.0), (0, 0, 0.9), lens=40)
c.save(NAME)
