"""Helpers shared by the asset build scripts: scene reset, materials, simple mesh builders, export."""

import math
from pathlib import Path

import bmesh
import bpy


def repo_root(script_file):
    """The repository root (the folder with package.json) above a script in assets/blender/."""
    path = Path(script_file).resolve()
    return next(p for p in path.parents if (p / "package.json").exists())


def srgb(r, g, b):
    """8-bit sRGB (as sampled from a sprite) to the linear RGB that Blender materials take."""
    def lin(c):
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return (lin(r), lin(g), lin(b))


def reference_image(name, path, width, height, location=(-2.0, 0.0, 0.0)):
    """Show an image (e.g. a sprite rendered by tools/extract-sprites.mjs) as a flat, unlit plane
    beside the model, in a `reference` collection that is never exported. Sizes are in units.
    Does nothing if the file is missing (reference images are git-ignored)."""
    path = Path(path)
    if not path.exists():
        print(f"reference image not found, skipping: {path}")
        return None
    coll = bpy.data.collections.get("reference") or bpy.data.collections.new("reference")
    if coll.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(coll)

    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)

    image = bpy.data.images.load(str(path), check_existing=True)
    image.reload()
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    tex = next((n for n in nodes if n.type == "TEX_IMAGE"), None) or nodes.new("ShaderNodeTexImage")
    tex.image = image
    tex.interpolation = "Closest"  # keep the pixels crisp
    links = mat.node_tree.links
    links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
    links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    bsdf.inputs["Emission Strength"].default_value = 1.0
    bsdf.inputs["Roughness"].default_value = 1.0

    bm = bmesh.new()
    w, h = width / 2, height / 2
    verts = [bm.verts.new(co) for co in ((-w, -h, 0), (w, -h, 0), (w, h, 0), (-w, h, 0))]
    face = bm.faces.new(verts)
    uv = bm.loops.layers.uv.new()
    for loop, coord in zip(face.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
        loop[uv].uv = coord
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    obj.location = location
    obj.hide_render = True
    return obj


def reset_collection(name):
    """Delete the collection's objects (and their meshes) and return it empty, linked to the scene."""
    coll = bpy.data.collections.get(name)
    if coll:
        for obj in list(coll.objects):
            data = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if isinstance(data, bpy.types.Mesh) and data.users == 0:
                bpy.data.meshes.remove(data)
    else:
        coll = bpy.data.collections.new(name)
    if coll.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(coll)
    return coll


def material(name, color, metallic=0.0, roughness=0.5, emission=None, emission_strength=0.0):
    """Create or update a Principled BSDF material. Colours are linear RGB."""
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if emission:
        bsdf.inputs["Emission Color"].default_value = (*emission, 1.0)
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    mat.diffuse_color = (*color, 1.0)
    return mat


def loft(bm, sections, sides=8, mat_index=0, cap_start=True, cap_end=True):
    """Loft rings along +Y. Each section is (y, half_width, half_height, z_centre).

    A section with zero width and height collapses to a point (a nose or tail tip).
    """
    rings = []
    for y, w, h, z in sections:
        if w == 0 and h == 0:
            rings.append([bm.verts.new((0.0, y, z))])
            continue
        ring = []
        for i in range(sides):
            a = 2 * math.pi * (i + 0.5) / sides
            ring.append(bm.verts.new((w * math.cos(a), y, z + h * math.sin(a))))
        rings.append(ring)

    for r0, r1 in zip(rings, rings[1:]):
        if len(r0) == 1 and len(r1) == 1:
            continue
        for i in range(sides):
            j = (i + 1) % sides
            if len(r0) == 1:
                face = (r0[0], r1[j], r1[i])
            elif len(r1) == 1:
                face = (r0[i], r0[j], r1[0])
            else:
                face = (r0[i], r0[j], r1[j], r1[i])
            bm.faces.new(face).material_index = mat_index

    if cap_start and len(rings[0]) > 1:
        bm.faces.new(list(reversed(rings[0]))).material_index = mat_index
    if cap_end and len(rings[-1]) > 1:
        bm.faces.new(rings[-1]).material_index = mat_index


def slab(bm, outline, thickness, z=0.0, mat_index=0, mirror_x=False):
    """Extrude a 2D outline in the XY plane (counter-clockwise seen from above) by `thickness`."""
    if mirror_x:
        outline = [(-x, y) for x, y in reversed(outline)]
    top = [bm.verts.new((x, y, z + thickness / 2)) for x, y in outline]
    bottom = [bm.verts.new((x, y, z - thickness / 2)) for x, y in outline]
    bm.faces.new(top).material_index = mat_index
    bm.faces.new(list(reversed(bottom))).material_index = mat_index
    n = len(outline)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((bottom[i], bottom[j], top[j], top[i])).material_index = mat_index


def fin(bm, base, tip_offset, length, height, thickness, mat_index=0):
    """A thin swept fin: base is (x, y, z) of its leading root corner; tip_offset leans the tip out (x)."""
    x, y, z = base
    t = thickness / 2
    tx = x + tip_offset
    pts = [
        ((x, y, z), (x, y - length, z)),
        ((tx, y - length * 0.55, z + height), (tx, y - length, z + height)),
    ]
    (r0, r1), (t0, t1) = pts
    verts = []
    for px, py, pz in (r0, r1, t1, t0):
        verts.append((bm.verts.new((px - t, py, pz)), bm.verts.new((px + t, py, pz))))
    left = [v[0] for v in verts]
    right = [v[1] for v in verts]
    bm.faces.new(left).material_index = mat_index
    bm.faces.new(list(reversed(right))).material_index = mat_index
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new((left[j], left[i], right[i], right[j])).material_index = mat_index


def shift_x(bm, start, dx):
    """Move every vertex added since index `start` along X (loft builds on the centreline)."""
    bm.verts.ensure_lookup_table()
    for v in bm.verts[start:]:
        v.co.x += dx


def mesh_object(name, bm, materials, collection, smooth=False):
    """Turn a bmesh into an object with the given material slots, flat or smooth shaded."""
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = smooth
    for mat in materials:
        mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj


def export_glb(objects, path, image_format="AUTO"):
    """Export only `objects` to a .glb (Y-up, modifiers applied). Textured models (texture_bake.py)
    pass image_format="WEBP" so their baked maps stay small (EXT_texture_webp; three.js reads it)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    for obj in bpy.context.view_layer.objects:
        obj.select_set(False)
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.export_scene.gltf(
        filepath=str(path),
        export_format="GLB",
        use_selection=True,
        export_yup=True,
        export_apply=True,
        export_cameras=False,
        export_lights=False,
        export_extras=True,  # custom properties: frame tags on parts and materials (frame_part, palette_material)
        export_image_format=image_format,
        export_image_quality=85,
    )
    return path


# --- Models that replace sprites (DECISIONS.md D15) ---------------------------------------------

def load_sprite(root, name):
    """reference/models/<name>/sprite.json, written by `npm run catalogue`: what the model replaces,
    each frame's pixels as palette indices (rows of space-separated ints, -1 = transparent) and the
    colours of those indices. Returns the dict with each frame's `pixels` parsed into lists of ints."""
    import json
    data = json.loads((Path(root) / "reference" / "models" / name / "sprite.json").read_text())
    for frame in data["frames"]:
        frame["pixels"] = [[int(v) for v in row.split()] for row in frame["pixels"]]
    return data


def palette_material(sprite, index, tag, metallic=0.3, roughness=0.5, emission_strength=0.0, frames=None):
    """A material for palette colour `index` of a sprite (load_sprite), named pal_<index>_<tag>.

    In game the colour comes from the live palette by that index (level palettes, fades and the
    hit flash all apply), so pick the index of the sprite pixels the part stands for. `tag` keeps
    names unique when several models share a Blender session; use the model name, plus the part's
    name for a material with `frames`. Emission makes the part glow in the same palette colour.

    `frames` animates the colour (DECISIONS.md D17): {sprite frame: palette index} for the frames
    where the part shows another colour than `index`, e.g. {91: 122, 93: 124} for a glow that
    brightens. Those indices may come from any frame of the sprite."""
    def rgb_of(i):
        rgb = sprite["colors"].get(str(i))
        if rgb is None:
            raise ValueError(f"palette index {i} isn't used by {sprite['name']}; pick one of {list(sprite['colors'])}")
        return srgb(*rgb)
    color = rgb_of(index)
    mat = material(f"pal_{index}_{tag}", color, metallic=metallic, roughness=roughness,
                   emission=color if emission_strength else None, emission_strength=emission_strength)
    if frames:
        mat["tyrian_frame_pal"] = {str(int(f)): int(i) for f, i in frames.items()}
        mat["tyrian_frame_rgb"] = {str(int(f)): list(rgb_of(i)) for f, i in frames.items()}  # for previews
    elif "tyrian_frame_pal" in mat:
        del mat["tyrian_frame_pal"]
        del mat["tyrian_frame_rgb"]
    return mat


def frame_part(obj, frames):
    """Show `obj` only on these sprite frames (DECISIONS.md D17): a flame of one length, a light
    that's on, a hatch that's open. `frames` are sprite indices as in sprite.json (each frame's
    `index`). Parts without frames always show. Export it with the rest of the model."""
    obj["tyrian_frames"] = sorted(int(f) for f in frames)
    return obj


def outline_shell(obj, collection, voxel=0.012, faces=3000, smooth=6):
    """A smooth, closed copy of `obj` for the game's ink outline only (DECISIONS.md D51): a voxel
    remesh (it closes the panel gaps), smoothed, decimated to about `faces` faces and smooth
    shaded. The outline (three's OutlineEffect, an inverted hull
    pushed out along the normals) breaks into whiskers along hard edges with split normals and
    strokes every separate plate; drawn from this shell instead it is one clean contour. The shell
    gets the material `outline_shell` and the node extra `tyrian_outline: true`; the game draws
    it only in the outline pass (src/render/models.ts) and turns the model's own outline off."""
    me = obj.data.copy()
    me.materials.clear()
    shell = bpy.data.objects.new(f"{obj.name}_outline", me)
    collection.objects.link(shell)
    shell.matrix_world = obj.matrix_world.copy()
    for mod in list(shell.modifiers):
        shell.modifiers.remove(mod)
    rm = shell.modifiers.new("remesh", "REMESH")
    rm.mode = "VOXEL"
    rm.voxel_size = voxel
    rm.adaptivity = 0.0
    rm.use_smooth_shade = True
    _apply_modifiers(shell)
    # Keep the outer surface only (an open model can leave inner shells).
    bm = bmesh.new()
    bm.from_mesh(shell.data)
    islands = []
    seen = set()
    for v in bm.verts:
        if v.index in seen:
            continue
        stack, isl = [v], []
        while stack:
            x = stack.pop()
            if x.index in seen:
                continue
            seen.add(x.index)
            isl.append(x)
            stack.extend(e.other_vert(x) for e in x.link_edges)
        islands.append(isl)
    def extent(isl):
        xs = [v.co.x for v in isl]
        ys = [v.co.y for v in isl]
        return (max(xs) - min(xs)) * (max(ys) - min(ys))
    keep = max(islands, key=extent)
    keep_ids = {v.index for v in keep}
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index not in keep_ids], context="VERTS")
    bm.to_mesh(shell.data)
    bm.free()
    # Smooth (relaxing the voxel steps and pulling it a hair inside the model's convex edges, so
    # its back faces stay under the model in creases instead of drawing stray lines), then thin.
    sm = shell.modifiers.new("smooth", "SMOOTH")
    sm.factor = 0.6
    sm.iterations = smooth
    n = len(shell.data.polygons)
    if n > faces:
        dec = shell.modifiers.new("decimate", "DECIMATE")
        dec.ratio = faces / n
    _apply_modifiers(shell)
    shell.data.shade_smooth()
    shell.data.materials.append(material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0))
    shell["tyrian_outline"] = True
    return shell


def _apply_modifiers(obj):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    for mod in list(obj.modifiers):
        bpy.ops.object.modifier_apply(modifier=mod.name)


def export_sprite_model(root, objects, model, sprites, image_format="AUTO"):
    """Export `objects` to public/models/<model>.glb and register the sprites they replace in
    src/render/spriteModels/<basename>.json. `sprites` is the list of {sheet, size, frames} (and
    `bank` for player ships) this model replaces, usually load_sprite(...)["sprites"], or a subset
    of its frames when an animation needs more than one model. A model that bakes its own maps
    passes image_format="WEBP" (as export_glb)."""
    import json
    root = Path(root)
    out = export_glb(objects, root / "public" / "models" / f"{model}.glb", image_format=image_format)
    entry = root / "src" / "render" / "spriteModels" / f"{Path(model).name}.json"
    entry.parent.mkdir(parents=True, exist_ok=True)
    entry.write_text(json.dumps({"model": model, "sprites": sprites}, indent=1) + "\n")
    faces = sum(len(o.data.polygons) for o in objects if o.type == "MESH")
    print(f"exported {out} ({out.stat().st_size} bytes, {faces} faces) and {entry}")
    return out


def _render_view(scene, camera, path):
    scene.camera = camera
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def render_preview(objects, out_png, sprite_png=None, size=2, view_px=320, frame=None):
    """Render the model beside its sprite into one PNG to compare them: the sprite, a top-down
    orthographic view at the same scale, the in-game view (from the bottom of the screen, tilted
    like the game camera) and a three-quarter view. Only `objects` are shown. `size` is the sprite's
    size in tiles (1 = 12x14 px, 2 = 24x28 px), or its (width, height) in px for anything else (a frame's
`width` and `height` in sprite.json). With `frame` (a sprite index), parts and colours tagged for
frames (frame_part, palette_material frames=) show as on that frame. Works headless."""
    import tempfile
    import numpy as np
    from mathutils import Vector

    scene = bpy.context.scene
    hidden = [o for o in scene.objects if o not in objects and not o.hide_render]
    if frame is not None:
        hidden += [o for o in objects if "tyrian_frames" in o and int(frame) not in list(o["tyrian_frames"]) and not o.hide_render]
    for o in hidden:
        o.hide_render = True
    recoloured = []
    if frame is not None:
        mats = {m for o in objects if o.type == "MESH" for m in o.data.materials if m}
        for m in mats:
            rgb = m.get("tyrian_frame_rgb", {}).get(str(int(frame)))
            if rgb is not None:
                recoloured.append((m, tuple(m.diffuse_color)))
                m.diffuse_color = (*rgb, 1.0)
    try:
        scene.render.engine = "BLENDER_WORKBENCH"
    except TypeError as err:  # the message lists the valid engines
        scene.render.engine = next(e for e in str(err).replace("'", " ").replace(",", " ").split() if "WORKBENCH" in e)
    shading = scene.display.shading
    shading.light = "STUDIO"
    shading.color_type = "MATERIAL"
    shading.show_cavity = True
    shading.show_object_outline = True
    scene.render.resolution_x = scene.render.resolution_y = view_px
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    if scene.world is None:
        scene.world = bpy.data.worlds.new("preview")
    scene.world.color = (0.03, 0.03, 0.04)

    w, h = (size[0] / 12, size[1] / 12) if isinstance(size, (tuple, list)) else (size, size * 14 / 12)  # units
    extent = max(w, h) * 1.15
    cams = []
    def camera(name, location, look_at, ortho=None, lens=50):
        data = bpy.data.cameras.new(name)
        if ortho:
            data.type = "ORTHO"
            data.ortho_scale = ortho
        else:
            data.lens = lens
        cam = bpy.data.objects.new(name, data)
        scene.collection.objects.link(cam)
        cam.location = location
        direction = Vector(look_at) - Vector(location)
        cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        cams.append(cam)
        return cam

    d = extent * 1.8
    top = camera("preview_top", (0, 0, 10), (0, 0, 0), ortho=extent)
    top.rotation_euler = (0, 0, 0)
    game = camera("preview_game", (0, -d * 0.55, d * 0.85), (0, 0, 0))
    three = camera("preview_34", (d * 0.6, -d * 0.6, d * 0.45), (0, 0, 0))

    tmp = Path(tempfile.mkdtemp())
    panels = []
    for cam in (top, game, three):
        path = tmp / f"{cam.name}.png"
        _render_view(scene, cam, path)
        img = bpy.data.images.load(str(path))
        px = np.array(img.pixels[:], dtype=np.float32).reshape(img.size[1], img.size[0], 4)
        bpy.data.images.remove(img)
        panels.append(px)

    # The sprite, nearest-neighbour scaled to the same scale as the top view, on the same background.
    bg = np.zeros((view_px, view_px, 4), dtype=np.float32)
    bg[...] = panels[0][0, 0]
    if sprite_png and Path(sprite_png).exists():
        img = bpy.data.images.load(str(sprite_png))
        sw, sh = img.size
        spx = np.array(img.pixels[:], dtype=np.float32).reshape(sh, sw, 4)  # bottom-up rows
        bpy.data.images.remove(img)
        scale = view_px / extent  # image px per unit
        tw, th = int(round(w * scale)), int(round(h * scale))
        ys = (np.arange(th) * sh / th).astype(int)
        xs = (np.arange(tw) * sw / tw).astype(int)
        small = spx[ys][:, xs]
        y0, x0 = (view_px - th) // 2, (view_px - tw) // 2
        region = bg[y0:y0 + th, x0:x0 + tw]
        a = small[..., 3:4]
        region[..., :3] = small[..., :3] * a + region[..., :3] * (1 - a)
    sheet = np.concatenate([bg] + panels, axis=1)
    out = bpy.data.images.new("preview_sheet", sheet.shape[1], sheet.shape[0], alpha=True)
    out.pixels[:] = sheet.ravel()
    out.filepath_raw = str(out_png)
    out.file_format = "PNG"
    Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    out.save()
    bpy.data.images.remove(out)

    for cam in cams:
        data = cam.data
        bpy.data.objects.remove(cam, do_unlink=True)
        bpy.data.cameras.remove(data)
    for o in hidden:
        o.hide_render = False
    for m, colour in recoloured:
        m.diffuse_color = colour
    print(f"preview {out_png}")
    return out_png


def render_frame_previews(objects, out_png, sprite, root, view_px=200):
    """render_preview for every frame of a sprite (load_sprite), stacked top to bottom in one PNG:
    each row is that frame's sprite, then the model as it is on that frame. For checking an
    animation (frame_part, palette_material frames=)."""
    import tempfile
    import numpy as np
    tmp = Path(tempfile.mkdtemp())
    rows = []
    for f in sprite["frames"]:
        path = tmp / f"{f['index']}.png"
        ref = Path(root) / "reference" / "models" / sprite["name"] / f["image"]
        render_preview(objects, path, ref, size=(f.get("width", f["size"] * 12), f.get("height", f["size"] * 14)),
                       view_px=view_px, frame=f["index"])
        img = bpy.data.images.load(str(path))
        rows.append(np.array(img.pixels[:], dtype=np.float32).reshape(img.size[1], img.size[0], 4))
        bpy.data.images.remove(img)
    sep = np.ones((2, rows[0].shape[1], 4), dtype=np.float32)
    stack = []
    for r in reversed(rows):  # Blender images are bottom-up
        stack += [r, sep]
    sheet = np.concatenate(stack[:-1], axis=0)
    out = bpy.data.images.new("frame_previews", sheet.shape[1], sheet.shape[0], alpha=True)
    out.pixels[:] = sheet.ravel()
    out.filepath_raw = str(out_png)
    out.file_format = "PNG"
    Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    out.save()
    bpy.data.images.remove(out)
    print(f"frame previews {out_png}")
    return out_png


def split_assembly(obj, layout, collection=None):
    """Cut a model of a whole multi-piece object (a boss or big structure: several 2x2 enemies side
    by side, sprite.json `assemblyLayout`) into one object per piece.

    Build `obj` in assembly coordinates: Blender X = cx / 12 and Y = -cy / 12 for a point at screen
    pixel (cx, cy) as given in the layout (pick any origin; only differences matter, so subtract a
    common offset if you like, and pass the same offset here as layout entries). `layout` is a list
    of (model_name, cx, cy): each piece's centre in screen pixels. Each piece keeps the part of
    `obj` inside its 24x28 px box, with the cut faces filled, moved so its centre is the origin.
    Returns {model_name: object}. `obj` is left as it was."""
    result = {}
    coll = collection or obj.users_collection[0]
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)
        hw, hh = 12 / 12, 14 / 12
        for co, no in (((x0 - hw, 0, 0), (-1, 0, 0)), ((x0 + hw, 0, 0), (1, 0, 0)),
                       ((0, y0 - hh, 0), (0, -1, 0)), ((0, y0 + hh, 0), (0, 1, 0))):
            geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
            cut = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, clear_outer=True)
            edges = [e for e in cut["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
            if edges:
                bmesh.ops.holes_fill(bm, edges=edges, sides=0)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        mesh = bpy.data.meshes.new(name)
        bm.to_mesh(mesh)
        bm.free()
        for mat in obj.data.materials:
            mesh.materials.append(mat)
        piece = bpy.data.objects.new(name, mesh)
        coll.objects.link(piece)
        result[name] = piece
    return result
