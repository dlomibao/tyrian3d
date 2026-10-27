"""Helpers shared by the picture scripts (assets/art/*.py): an empty scene at the pictures' size,
cameras, the game's models, procedural materials and the WebP output.

Run a picture script headless from the repository root:

    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
        --python assets/art/<name>.py               # writes public/art/<name>.webp
        --python assets/art/<name>.py -- --preview  # quarter size, few samples, to reference/art/
"""

import math
import os
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "package.json").exists())
MODELS = ROOT / "public" / "models"
OUT = ROOT / "public" / "art"
PREVIEW_OUT = ROOT / "reference" / "art"

# The originals are 320x200 (8:5); the new pictures keep the shape at 1920x1200.
WIDTH, HEIGHT = 1920, 1200
# Each WebP stays under this many bytes; save() lowers the quality until it fits.
MAX_BYTES = 600 * 1024

ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PREVIEW = "--preview" in ARGV


def srgb(r, g, b):
    """8-bit sRGB (as sampled from a picture) to the linear RGB that Blender materials take."""
    def lin(c):
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return (lin(r), lin(g), lin(b))


def new_scene(engine="CYCLES", samples=128, exposure=0.0, look="None"):
    """An empty scene at 1920x1200. Cycles renders on the GPU (Metal) when there is one."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.resolution_x, scene.render.resolution_y = WIDTH, HEIGHT
    scene.render.resolution_percentage = 25 if PREVIEW else 100
    try:
        scene.render.engine = engine
    except TypeError as e:  # the message lists the valid engines
        raise SystemExit(f"engine {engine}: {e}")
    if engine == "CYCLES":
        prefs = bpy.context.preferences.addons["cycles"].preferences
        try:
            prefs.compute_device_type = "METAL"
            prefs.get_devices()
            for d in prefs.devices:
                d.use = d.type == "METAL"
            scene.cycles.device = "GPU" if any(d.use for d in prefs.devices) else "CPU"
        except TypeError:
            scene.cycles.device = "CPU"
        scene.cycles.samples = 16 if PREVIEW else samples
        scene.cycles.use_denoising = True
        scene.cycles.max_bounces = 6
    else:
        scene.eevee.taa_render_samples = 16 if PREVIEW else samples
    scene.view_settings.exposure = exposure
    try:
        scene.view_settings.look = look
    except TypeError:
        pass
    world = bpy.data.worlds.new("world")
    scene.world = world
    world.use_nodes = True
    world_color((0, 0, 0))
    return scene


def world_color(color, strength=1.0):
    """A plain world colour (linear RGB)."""
    nodes = bpy.context.scene.world.node_tree.nodes
    bg = next(n for n in nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (*color, 1)
    bg.inputs["Strength"].default_value = strength


def look_at(obj, target, roll=0.0):
    """Point a camera or light (which look down their -Z, +Y up) at `target`."""
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    obj.rotation_euler.rotate_axis("Z", roll)


def camera(location, target, lens=50.0, ortho_scale=None, shift=(0.0, 0.0)):
    """The scene camera at `location` looking at `target`: perspective with `lens` (mm), or
    orthographic `ortho_scale` units wide."""
    data = bpy.data.cameras.new("camera")
    if ortho_scale:
        data.type = "ORTHO"
        data.ortho_scale = ortho_scale
    else:
        data.lens = lens
    data.shift_x, data.shift_y = shift
    data.clip_end = 10000
    cam = bpy.data.objects.new("camera", data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = location
    look_at(cam, target)
    bpy.context.scene.camera = cam
    return cam


def light(kind, location, target=(0, 0, 0), energy=10.0, color=(1, 1, 1), size=0.5, angle=None):
    """A light ('SUN', 'AREA', 'POINT', 'SPOT') aimed at `target`."""
    data = bpy.data.lights.new(kind.lower(), kind)
    data.energy = energy
    data.color = color
    if kind == "SUN":
        data.angle = math.radians(angle if angle is not None else 2.0)
    elif kind == "AREA":
        data.size = size
    else:
        data.shadow_soft_size = size
    obj = bpy.data.objects.new(kind.lower(), data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    look_at(obj, target)
    return obj


def model(name, location=(0, 0, 0), rotation=(0, 0, 0), scale=1.0):
    """Import public/models/<name>.glb under an empty placed at `location`, rotated (degrees, XYZ)
    and scaled. The models are in the game's axes (1 unit = 12 sprite pixels, nose along +Y, up +Z
    once imported back from glTF's Y-up)."""
    path = MODELS / f"{name}.glb"
    if not path.exists():
        path = next(MODELS.rglob(f"{name}.glb"))
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    new = [o for o in bpy.data.objects if o not in before]
    root = bpy.data.objects.new(f"{name}_root", None)
    bpy.context.scene.collection.objects.link(root)
    for o in new:
        if o.parent is None:
            o.parent = root
    root.location = location
    root.rotation_euler = [math.radians(a) for a in rotation]
    root.scale = (scale, scale, scale)
    return root


def aim(obj, forward, up):
    """Turn `obj` so its +Y (a model's nose) points along `forward` and its +Z (its top) as near
    `up` as possible."""
    from mathutils import Matrix
    y = Vector(forward).normalized()
    x = y.cross(Vector(up)).normalized()
    z = x.cross(y)
    obj.rotation_euler = Matrix((x, y, z)).transposed().to_euler()


def camera_axes(cam):
    """The camera's right, up and viewing directions in world space."""
    m = cam.matrix_world.to_3x3()
    return m.col[0].normalized(), m.col[1].normalized(), -m.col[2].normalized()


def model_materials(root):
    """Every material used under an imported model's root."""
    mats = set()
    for o in root.children_recursive:
        if o.type == "MESH":
            mats.update(s.material for s in o.material_slots if s.material)
    return mats


def tint_model(root, metallic=None, roughness=None, darken=1.0):
    """Adjust an imported model's materials for a close-up (the game's are tuned for a small view)."""
    for m in model_materials(root):
        b = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if not b:
            continue
        if metallic is not None:
            b.inputs["Metallic"].default_value = metallic
        if roughness is not None:
            b.inputs["Roughness"].default_value = roughness
        c = b.inputs["Base Color"].default_value
        b.inputs["Base Color"].default_value = (c[0] * darken, c[1] * darken, c[2] * darken, c[3])


def material(name, color=(0.8, 0.8, 0.8), metallic=0.0, roughness=0.5, emission=None, emission_strength=0.0):
    """A Principled BSDF material (linear RGB). Returns (material, its node tree)."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    b = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Roughness"].default_value = roughness
    if emission is not None:
        b.inputs["Emission Color"].default_value = (*emission, 1)
        b.inputs["Emission Strength"].default_value = emission_strength
    return mat


def emission(name, color, strength=1.0):
    """A pure emission material (no shading), for skies, glows and grids."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1)
    em.inputs["Strength"].default_value = strength
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return mat


def rim_glow(name, color, strength=2.0, start=0.5, power=2.5):
    """An atmosphere for a shell slightly bigger than a planet: clear, adding light that grows
    toward the shell's silhouette (where the view grazes it) and fades out past the planet's edge."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = node(nt, "ShaderNodeOutputMaterial")
    lw = node(nt, "ShaderNodeLayerWeight", Blend=0.5)
    edge = node(nt, "ShaderNodeMapRange", **{"From Min": start, "From Max": 1.0, "To Min": 0.0, "To Max": 1.0})
    link(nt, lw.outputs["Facing"], edge.inputs["Value"])
    pw = node(nt, "ShaderNodeMath", p_operation="POWER", values={1: power})
    link(nt, edge.outputs[0], pw.inputs[0])
    k = node(nt, "ShaderNodeMath", p_operation="MULTIPLY", values={1: strength})
    link(nt, pw.outputs[0], k.inputs[0])
    em = node(nt, "ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1)
    link(nt, k.outputs[0], em.inputs["Strength"])
    add = node(nt, "ShaderNodeAddShader")
    link(nt, em.outputs[0], add.inputs[0])
    link(nt, node(nt, "ShaderNodeBsdfTransparent").outputs[0], add.inputs[1])
    link(nt, add.outputs[0], out.inputs["Surface"])
    return mat


def node(nt, kind, values=None, **inputs):
    """Add a shader node and set its inputs by name (`values` also by index) and, for p_<name>,
    its properties."""
    n = nt.nodes.new(kind)
    for k, v in (values or {}).items():
        n.inputs[k].default_value = v
    for k, v in inputs.items():
        if k.startswith("p_"):
            setattr(n, k[2:], v)
        else:
            n.inputs[k].default_value = v
    return n


def ramp(nt, stops, interpolation="LINEAR"):
    """A colour ramp node from [(position, (r, g, b)), ...] (linear RGB)."""
    r = nt.nodes.new("ShaderNodeValToRGB")
    r.color_ramp.interpolation = interpolation
    els = r.color_ramp.elements
    while len(els) < len(stops):
        els.new(0.5)
    for el, (pos, col) in zip(els, stops):
        el.position = pos
        el.color = (*col, 1) if len(col) == 3 else col
    return r


def link(nt, a, b):
    nt.links.new(a, b)


def mesh_object(name, mesh, mat=None, location=(0, 0, 0)):
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    if mat:
        obj.data.materials.append(mat)
    return obj


def primitive(kind, name, mat=None, **kw):
    """bpy.ops.mesh.primitive_<kind>_add(**kw) as a named object with a material."""
    getattr(bpy.ops.mesh, f"primitive_{kind}_add")(**kw)
    obj = bpy.context.active_object
    obj.name = name
    if mat:
        obj.data.materials.append(mat)
    return obj


def smooth(obj, subdivisions=0):
    """Smooth-shade an object, optionally with a subdivision surface."""
    for p in obj.data.polygons:
        p.use_smooth = True
    if subdivisions:
        m = obj.modifiers.new("subsurf", "SUBSURF")
        m.levels = m.render_levels = subdivisions
    return obj


def starfield(nt, vector, scale=400.0, density=0.012, strength=4.0):
    """Stars for a world or a backdrop: Voronoi cells whose nearest point is very close become a
    star, each a different brightness. Returns the node whose Color output is the stars."""
    vor = node(nt, "ShaderNodeTexVoronoi", Scale=scale, Randomness=1.0)
    link(nt, vector, vor.inputs["Vector"])
    # Distance -> a tiny disc; the cell colour decides how bright (most cells get no star).
    disc = node(nt, "ShaderNodeMapRange", **{"From Min": 0.0, "From Max": 0.06, "To Min": 1.0, "To Max": 0.0})
    link(nt, vor.outputs["Distance"], disc.inputs["Value"])
    sep = node(nt, "ShaderNodeSeparateColor")
    link(nt, vor.outputs["Color"], sep.inputs["Color"])
    keep = node(nt, "ShaderNodeMapRange", **{"From Min": 1.0 - density, "From Max": 1.0, "To Min": 0.0, "To Max": strength})
    link(nt, sep.outputs[0], keep.inputs["Value"])
    mul = node(nt, "ShaderNodeMath", p_operation="MULTIPLY", p_use_clamp=False)
    link(nt, disc.outputs[0], mul.inputs[0])
    link(nt, keep.outputs[0], mul.inputs[1])
    return mul


def save(name):
    """Render and write public/art/<name>.webp (lowering the quality until it's under MAX_BYTES),
    or, with --preview, reference/art/<name>.png."""
    scene = bpy.context.scene
    bpy.ops.render.render()
    image = bpy.data.images["Render Result"]
    if PREVIEW:
        PREVIEW_OUT.mkdir(parents=True, exist_ok=True)
        path = PREVIEW_OUT / f"{name}.png"
        scene.render.image_settings.file_format = "PNG"
        image.save_render(str(path), scene=scene)
        print(f"wrote {path}")
        return path
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{name}.webp"
    scene.render.image_settings.file_format = "WEBP"
    scene.render.image_settings.color_mode = "RGB"
    for quality in (95, 90, 85, 80, 75, 70, 65, 60, 55, 50):
        scene.render.image_settings.quality = quality
        image.save_render(str(path), scene=scene)
        size = os.path.getsize(path)
        if size <= MAX_BYTES:
            break
    print(f"wrote {path}: {size // 1024} KB at quality {quality}")
    return path
