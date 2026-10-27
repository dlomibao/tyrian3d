"""Picture 5: the dark violet planet behind most of the story text (episode script `]P 005`).

A gas giant centred on black, almost all in shadow, lit only along its left limb, so the white
text over it stays readable. Writes public/art/story_planet.webp.
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as c  # noqa: E402

NAME = "story_planet"

c.new_scene(samples=96)

# The world: black with very faint, sparse stars.
wnt = c.bpy.context.scene.world.node_tree
bg = next(n for n in wnt.nodes if n.type == "BACKGROUND")
coord = c.node(wnt, "ShaderNodeTexCoord")
stars = c.starfield(wnt, coord.outputs["Generated"], scale=900, density=0.006, strength=0.25)
c.link(wnt, stars.outputs[0], bg.inputs["Color"])

# The planet: banded violet clouds (stretched noise), turbulent where the bands meet.
mat = c.bpy.data.materials.new("planet")
mat.use_nodes = True
nt = mat.node_tree
bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
bsdf.inputs["Roughness"].default_value = 0.85
tc = c.node(nt, "ShaderNodeTexCoord")
mapping = c.node(nt, "ShaderNodeMapping")
mapping.inputs["Scale"].default_value = (1.0, 1.0, 7.0)  # bands along the equator
c.link(nt, tc.outputs["Object"], mapping.inputs["Vector"])
warp = c.node(nt, "ShaderNodeTexNoise", Scale=3.0, Detail=8.0, Roughness=0.6)
c.link(nt, tc.outputs["Object"], warp.inputs["Vector"])
mix = c.node(nt, "ShaderNodeMix", p_data_type="VECTOR", Factor=0.18)
c.link(nt, mapping.outputs[0], mix.inputs[4])
c.link(nt, warp.outputs["Color"], mix.inputs[5])
bands = c.node(nt, "ShaderNodeTexNoise", Scale=1.6, Detail=10.0, Roughness=0.55, Distortion=0.4)
c.link(nt, mix.outputs[1], bands.inputs["Vector"])
col = c.ramp(nt, [
    (0.25, c.srgb(20, 10, 48)),
    (0.45, c.srgb(48, 22, 92)),
    (0.55, c.srgb(86, 34, 128)),
    (0.70, c.srgb(140, 52, 170)),
])
c.link(nt, bands.outputs["Fac"], col.inputs["Fac"])
c.link(nt, col.outputs["Color"], bsdf.inputs["Base Color"])
bump = c.node(nt, "ShaderNodeBump", Strength=0.15)
c.link(nt, bands.outputs["Fac"], bump.inputs["Height"])
c.link(nt, bump.outputs[0], bsdf.inputs["Normal"])

planet = c.primitive("uv_sphere", "planet", mat, segments=128, ring_count=64, radius=1.0)
c.smooth(planet)
planet.rotation_euler = (math.radians(8), math.radians(-14), 0)

# A thin atmosphere shell that scatters the light at the limb.
atmo = c.bpy.data.materials.new("atmosphere")
atmo.use_nodes = True
ant = atmo.node_tree
ant.nodes.clear()
out = c.node(ant, "ShaderNodeOutputMaterial")
vol = c.node(ant, "ShaderNodeVolumeScatter", Density=2.2, Anisotropy=0.55)
vol.inputs["Color"].default_value = (*c.srgb(170, 90, 255), 1)
c.link(ant, vol.outputs[0], out.inputs["Volume"])
shell = c.primitive("uv_sphere", "atmosphere", atmo, segments=96, ring_count=48, radius=1.035)
c.smooth(shell)

# Lit from behind and to the left: a crescent of light on the left limb only.
c.light("SUN", (-6, 2.2, 1.0), (0, 0, 0), energy=4.0, color=c.srgb(235, 170, 255), angle=1.0)
# A whisper of fill so the night side isn't pure black.
c.light("SUN", (3, -5, -1), (0, 0, 0), energy=0.25, color=c.srgb(110, 90, 220))

c.camera((0, -5.9, 0.1), (0, 0, 0.0), lens=50)
c.save(NAME)
