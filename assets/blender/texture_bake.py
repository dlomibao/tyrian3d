"""Texture a built model from its concept maps: detail, baked shadowing and fine relief.

    blender --background --factory-startup --python assets/blender/texture_bake.py -- <name> [--size 512]
    blender --background --factory-startup --python assets/blender/texture_bake.py -- tile:<entry> [--size N]

Runs after the model's own script has exported it: tools/build-models.sh runs it after building any
model that has concept maps. Needs assets/blender/textures/<name>/ from tools/concept_maps.py, and
for an assembly .shape/<name>/regions.json (from tools/sprite_shape.py) for where each piece sits.

For each exported .glb of the model (one, or one per assembly piece, then one per extra animation
frame, src/render/spriteModels/<name>-f<k>.json):
- import it, placed in the sprite's frame;
- pack one texture layout ("bake" UVs) across all its meshes;
- bake a colour texture: the concept's greyscale detail, projected straight down onto surfaces that
  face up and fading to neutral on steep sides, times ambient occlusion (Cycles), so crevices and
  seams darken;
- bake a tangent-space normal texture from the concept's fine relief, the same way;
- wire both into every material: Base Color = texture x the material's own colour (the game sets
  that colour from the live palette, so fades and the hit flash still work), Normal = the normal map;
- export the .glb again in place (names, extras and frame tags kept).
A frame model with the same mesh as the first frame (the same parts moved or turned) takes the first
frame's texture and bake UVs loop by loop, so its detail turns with its parts; one whose mesh
differs is baked on its own from the same maps. Either way every frame is textured: a frame left
plain would flash lighter than the rest each time it's shown.
The textures are also written to assets/blender/textures/<name>/bake/.

Tile models (background structures, D34): `tile:<entry>` bakes the model of
src/render/tileModels/<entry>.json (public/models/<model>.glb, origin at the pattern's centre) with
the maps from `tools/concept_maps.py tile:<entry> --concept ...` in assets/blender/textures/<entry>/.
The texture size defaults to about 5 texels per tile px (512 to 2048).
"""

import json
import math
import re
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "proto"))
ROOT = next(p for p in HERE.parents if (p / "package.json").exists())
import common  # noqa: E402
from shape_model import model_paths, piece_path  # noqa: E402

PX = 1 / 12
AO_DISTANCE = 0.25  # units: about two sprite pixels
STEEP_LO, STEEP_HI = 0.35, 0.75  # |normal.z| below LO: side (neutral); above HI: top (full detail)


def tile_glbs(entry):
    """[(glb path, offset 0)] and the pattern's size in px for a tile model (src/render/tileModels/)."""
    doc = json.loads((ROOT / "src" / "render" / "tileModels" / f"{entry}.json").read_text())
    size = (len(doc["tiles"][0]) * 24, len(doc["tiles"]) * 28)
    return [(ROOT / "public" / "models" / f"{doc['model']}.glb", Vector((0, 0, 0)))], size


def glbs(name):
    """[(glb path, offset into the sprite's frame)] for the model or each assembly piece."""
    if name.startswith("tile:"):
        return tile_glbs(name[5:])
    if not name.startswith("assembly-"):
        # A plain model is one piece covering the whole sprite (tools/sprite_shape.py), so it needs no
        # regions.json: the sprite's size is in the concept maps' maps.json.
        entry = ROOT / "src" / "render" / "spriteModels" / f"{name}.json"
        path = json.loads(entry.read_text())["model"] if entry.exists() else "usp_talon"
        size = json.loads((ROOT / "assets/blender/textures" / name / "maps.json").read_text())["sprite_size"]
        return [(ROOT / "public" / "models" / f"{path}.glb", Vector((0, 0, 0)))], tuple(size)
    doc = json.loads((ROOT / ".shape" / name / "regions.json").read_text())
    W, H = doc["size"]
    paths = model_paths()
    out, seen = [], set()
    for p in doc["pieces"]:
        if name.startswith("assembly-"):
            path = piece_path(p["model"], p.get("frame"), paths)
        else:
            entry = ROOT / "src" / "render" / "spriteModels" / f"{name}.json"
            path = json.loads(entry.read_text())["model"] if entry.exists() else "usp_talon"
        if path in seen:
            continue
        seen.add(path)
        off = Vector(((p["x0"] + p["w"] / 2 - W / 2) * PX, -(p["y0"] + p["h"] / 2 - H / 2) * PX, 0))
        out.append((ROOT / "public" / "models" / f"{path}.glb", off))
    return out, (W, H)


def clear():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.images):
        for b in list(coll):
            if b.users == 0:
                coll.remove(b)


def load_image(path, non_color):
    img = bpy.data.images.load(str(path), check_existing=True)
    img.colorspace_settings.name = "Non-Color" if non_color else "sRGB"
    return img


def concept_uvs(meshes, size):
    """A "concept" UV layer: each vertex's place in the sprite, seen from straight above."""
    W, H = size
    for o in meshes:
        me = o.data
        uv = me.uv_layers.new(name="concept")
        mw = o.matrix_world
        for loop in me.loops:
            co = mw @ me.vertices[loop.vertex_index].co
            px = co.x / PX + W / 2
            py = H / 2 - co.y / PX
            uv.data[loop.index].uv = (px / W, 1 - py / H)


def bake_uvs(meshes):
    """A "bake" UV layer packed across all the meshes (Smart UV Project)."""
    for o in meshes:
        uv = o.data.uv_layers.new(name="bake")
        o.data.uv_layers.active = uv
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.01, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.004)
    bpy.ops.object.mode_set(mode="OBJECT")


def top_factor(nt):
    """Node output: 0 on steep sides, 1 on surfaces that face up or down (world normal)."""
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Normal"], sep.inputs[0])
    ab = nt.nodes.new("ShaderNodeMath")
    ab.operation = "ABSOLUTE"
    nt.links.new(sep.outputs["Z"], ab.inputs[0])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = STEEP_LO
    mr.inputs["From Max"].default_value = STEEP_HI
    nt.links.new(ab.outputs[0], mr.inputs["Value"])
    return mr.outputs["Result"]


def concept_tex(nt, img):
    uv = nt.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "concept"
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.extension = "EXTEND"
    nt.links.new(uv.outputs["UV"], tex.inputs["Vector"])
    return tex.outputs["Color"]


def target(nt, img):
    uv = nt.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "bake"
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = img
    nt.links.new(uv.outputs["UV"], t.inputs["Vector"])
    nt.nodes.active = t
    return t


def bake_material_colour(detail, neutral, out_img):
    m = bpy.data.materials.new("BAKE_COLOUR")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    f = top_factor(nt)
    det = concept_tex(nt, detail)
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs[6].default_value = (neutral, neutral, neutral, 1)  # A: neutral (sides)
    nt.links.new(f, mix.inputs[0])
    nt.links.new(det, mix.inputs[7])  # B: detail (tops)
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao.inputs["Distance"].default_value = AO_DISTANCE
    ao.samples = 16
    mul = nt.nodes.new("ShaderNodeMix")
    mul.data_type = "RGBA"
    mul.blend_type = "MULTIPLY"
    mul.inputs[0].default_value = 1.0
    nt.links.new(mix.outputs[2], mul.inputs[6])
    nt.links.new(ao.outputs["AO"], mul.inputs[7])
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(mul.outputs[2], em.inputs["Color"])
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    target(nt, out_img)
    return m


def bake_material_normal(height, out_img):
    m = bpy.data.materials.new("BAKE_NORMAL")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    f = top_factor(nt)
    h = concept_tex(nt, height)
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Distance"].default_value = 0.012
    nt.links.new(f, bump.inputs["Strength"])
    nt.links.new(h, bump.inputs["Height"])
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(bsdf.outputs[0], out.inputs["Surface"])
    target(nt, out_img)
    return m


def bake(meshes, mat, kind):
    saved = {o: [s.material for s in o.material_slots] for o in meshes}
    for o in meshes:
        if not o.material_slots:
            o.data.materials.append(mat)
        for s in o.material_slots:
            s.material = mat
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    kw = {"type": kind, "margin": 4, "use_clear": True}
    if kind == "NORMAL":
        kw["normal_space"] = "TANGENT"
    bpy.ops.object.bake(**kw)
    for o, mats in saved.items():
        for s, m in zip(o.material_slots, mats):
            s.material = m


def wire(materials, colour_img, normal_img):
    """Base Color = baked colour x the material's colour; Normal = baked normal map."""
    for m in materials:
        if m is None or not m.use_nodes:
            continue
        nt = m.node_tree
        bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf is None:
            continue
        uv = nt.nodes.new("ShaderNodeUVMap")
        uv.uv_map = "bake"
        ct = nt.nodes.new("ShaderNodeTexImage")
        ct.image = colour_img
        nt.links.new(uv.outputs["UV"], ct.inputs["Vector"])
        base = bsdf.inputs["Base Color"]
        colour = tuple(base.default_value)
        if base.is_linked:  # leave a material that's already textured alone
            continue
        mul = nt.nodes.new("ShaderNodeMix")
        mul.data_type = "RGBA"
        mul.blend_type = "MULTIPLY"
        mul.inputs[0].default_value = 1.0
        nt.links.new(ct.outputs["Color"], mul.inputs[6])
        mul.inputs[7].default_value = colour
        nt.links.new(mul.outputs[2], base)
        nt_ = nt.nodes.new("ShaderNodeTexImage")
        nt_.image = normal_img
        nt.links.new(uv.outputs["UV"], nt_.inputs["Vector"])
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nm.uv_map = "bake"
        nt.links.new(nt_.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])


def frame_glbs(name):
    """The model's other animation frames (src/render/spriteModels/<name>-f<k>.json: one model per
    frame, D17), in frame order. Each must be textured like the first, or the animation pops between
    textured and plain (darker and lighter) every frame."""
    if name.startswith(("tile:", "assembly-")):
        return []
    entries = [p for p in (ROOT / "src" / "render" / "spriteModels").glob(f"{name}-f*.json")
               if re.fullmatch(rf"{re.escape(name)}-f\d+", p.stem)]
    entries.sort(key=lambda p: int(p.stem.rsplit("-f", 1)[1]))
    return [ROOT / "public" / "models" / f"{json.loads(p.read_text())['model']}.glb" for p in entries]


def import_glb(glb, off):
    """Import a .glb placed in the sprite's frame: (all its objects, root objects, meshes)."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(glb))
    objs = [o for o in bpy.data.objects if o not in before]
    roots = [o for o in objs if o.parent is None]
    for o in roots:
        o.location = Vector(o.location) + off
    bpy.context.view_layer.update()
    meshes = [o for o in objs if o.type == "MESH"]
    for o in meshes:
        for uv in list(o.data.uv_layers):
            o.data.uv_layers.remove(uv)
    return objs, roots, meshes


def export_in_place(objs, roots, off, glb):
    for o in roots:
        o.location = Vector(o.location) - off
    bpy.context.view_layer.update()
    common.export_glb(objs, glb, image_format="WEBP")


def topology(meshes):
    """What has to match for one model's bake UVs to fit another loop by loop: the faces in order,
    each face's corner count and material. (Vertex indices don't: the glTF round trip merges
    vertices by position and normal, which differ once a part is turned.)"""
    return [[(p.loop_total, p.material_index) for p in o.data.polygons] for o in meshes]


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    name = argv[0]
    size = int(argv[argv.index("--size") + 1]) if "--size" in argv else 0
    tile = name.startswith("tile:")
    tex_dir = ROOT / "assets/blender/textures" / (name[5:] if tile else name)
    meta = json.loads((tex_dir / "maps.json").read_text())
    bake_dir = tex_dir / "bake"
    bake_dir.mkdir(exist_ok=True)

    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 32
    scene.cycles.device = "CPU"

    pieces, sprite_size = glbs(name)
    frames = frame_glbs(name)
    shared = None  # the first .glb's bake, for its other frames: (topology, bake UVs, images)
    for i, (glb, off) in enumerate(pieces + [(f, pieces[0][1]) for f in frames]):
        clear()
        is_frame = i >= len(pieces)
        objs, roots, meshes = import_glb(glb, off)
        if is_frame and shared and topology(meshes) == shared[0]:
            # Same mesh as the first frame, moved or turned: reuse its texture loop by loop, so the
            # detail turns with the parts and every frame has the same brightness.
            for o, uvs in zip(meshes, shared[1]):
                layer = o.data.uv_layers.new(name="bake")
                for d, co in zip(layer.data, uvs):
                    d.uv = co
            wire({s.material for o in meshes for s in o.material_slots}, *shared[2])
            export_in_place(objs, roots, off, glb)
            print(f"textured {glb.relative_to(ROOT)} (the first frame's texture)")
            continue
        detail = load_image(tex_dir / "detail.png", True)
        height = load_image(tex_dir / "height.png", True)
        concept_uvs(meshes, sprite_size)
        bake_uvs(meshes)
        if tile and not size:
            area = (sprite_size[0] * sprite_size[1]) ** 0.5 * 5
            px = int(min(2048, max(512, 2 ** round(math.log2(area)))))
        else:
            px = size or (512 if len(pieces) == 1 else 256)
        stem = glb.stem
        colour_img = bpy.data.images.new(f"{stem}-detail", px, px, alpha=False)
        normal_img = bpy.data.images.new(f"{stem}-normal", px, px, alpha=False)
        normal_img.colorspace_settings.name = "Non-Color"
        bake(meshes, bake_material_colour(detail, meta["neutral"], colour_img), "EMIT")
        bake(meshes, bake_material_normal(height, normal_img), "NORMAL")
        for img in (colour_img, normal_img):
            img.filepath_raw = str(bake_dir / f"{img.name}.png")
            img.file_format = "PNG"
            img.save()
        mats = {s.material for o in meshes for s in o.material_slots}
        wire(mats, colour_img, normal_img)
        for o in meshes:
            o.data.uv_layers.remove(o.data.uv_layers["concept"])
        if i == 0 and frames:
            for img in (colour_img, normal_img):
                img.use_fake_user = True  # kept through clear() for the other frames
            shared = (topology(meshes), [[tuple(d.uv) for d in o.data.uv_layers["bake"].data] for o in meshes],
                      (colour_img, normal_img))
        export_in_place(objs, roots, off, glb)
        what = "frame, baked on its own: its mesh differs from the first frame's" if is_frame else f"{len(meshes)} meshes"
        print(f"textured {glb.relative_to(ROOT)} ({what}, {px} px)")


main()
