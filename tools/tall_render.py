"""Renders for tools/tall_buildings.py measure (run by it in Blender):

    blender -b --factory-startup --python tools/tall_render.py -- <views.json>

For each view in views.json, two PNGs of the model in the pattern's frame (w x h px at `scale`):
`<name>.png`, its flat palette colours, and `<name>-kind.png`, red where the faces point up (roofs),
green on walls, blue on faces within 1 px of the base (its foot); and `foot.png`, the model's section
1 px above its base, filled, from straight above (its footprint). Objects marked `tall_ground` (the
ground a lib_tall model carries) and faces in plain materials (`..._plainTrue`: the island rock a
structure carries, D63) are left out; palette materials show their palette colour (`colors` in
views.json) whatever texture they wear. A view with a camera is the game's picture of it: every vertex moved along the camera's ray onto the ground plane (D6 places a draw so its
screen layout is the original's, which is the same as standing the model on the ground at its screen
point), keeping its height for which is in front; a model with the extra `tyrian_oblique` goes on the
rays the renderer gives it (src/render/remaster/structureInstances.ts). `screen_row` is where on the
playfield (px from its top) the pattern's centre is. A view without a camera is straight down,
orthographic.
"""

import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

PX = 1 / 12


def main():
    spec = json.loads(Path(sys.argv[sys.argv.index("--") + 1]).read_text())
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=spec["glb"])
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH" and not o.get("tyrian_outline")]
    # The ground a structure carries (lib_tall plate, island rock) is not the building.
    for o in meshes:
        if o.get("tall_ground"):
            o.hide_render = True
    meshes = [o for o in meshes if not o.get("tall_ground")]
    oblique = max([float(o.get("tyrian_oblique", 0) or 0) for o in bpy.context.scene.objects] + [0.0])
    w, h, scale = spec["w"], spec["h"], spec["scale"]
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "FLAT"
    scene.display.shading.color_type = "MATERIAL"
    scene.render.film_transparent = True
    scene.view_settings.view_transform = "Standard"
    scene.render.resolution_x, scene.render.resolution_y = w * scale, h * scale
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.display.render_aa = "OFF"
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = max(w, h) * PX
    cam.location = (0, 0, 50)
    cam.rotation_euler = (0, 0, 0)
    # Flat palette colours: a palette material (pal_<index>_...) shows its palette colour, whatever
    # texture it wears; others their base colour.
    colors = {int(k): v for k, v in spec.get("colors", {}).items()}
    for mat in bpy.data.materials:
        parts = mat.name.split("_")
        if parts[0] == "pal" and parts[1].isdigit() and int(parts[1]) in colors:
            mat.diffuse_color = (*[linear(c) for c in colors[int(parts[1])]], 1.0)
            continue
        bsdf = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None) if mat.use_nodes else None
        if bsdf:
            mat.diffuse_color = tuple(bsdf.inputs["Base Color"].default_value)
    # Island rock a structure carries (D63: plain palette materials) is ground too.
    import bmesh
    for o in meshes:
        plain = [i for i, m in enumerate(o.data.materials) if m and "plainTrue" in m.name]
        if not plain:
            continue
        bm = bmesh.new()
        bm.from_mesh(o.data)
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index in plain], context="FACES")
        bm.to_mesh(o.data)
        bm.free()
    kinds = {}
    for k, c in (("up", (1, 0, 0, 1)), ("wall", (0, 1, 0, 1)), ("base", (0, 0, 1, 1)), ("base_up", (1, 0, 1, 1)), ("base_wall", (0, 1, 1, 1))):
        m = bpy.data.materials.new(f"kind_{k}")
        m.diffuse_color = c
        kinds[k] = m
    # Bake the world transforms in (glTF Y-up comes in as Blender Z-up).
    originals = []
    for o in meshes:
        o.data = o.data.copy()
        o.data.transform(o.matrix_world)
        o.matrix_world.identity()
        originals.append([v.co.copy() for v in o.data.vertices])
    for view in spec["views"]:
        for o, co in zip(meshes, originals):
            for v, p in zip(o.data.vertices, co):
                v.co = place(p, view, oblique)
            o.data.update()
        render(scene, Path(spec["out"]) / f"{view['name']}.png")
        # The kind pass: per face by its true normal and height.
        saved = []
        for o, co in zip(meshes, originals):
            mats = list(o.data.materials)
            idx = [p.material_index for p in o.data.polygons]
            saved.append((mats, idx))
            o.data.materials.clear()
            for k in ("up", "wall", "base", "base_up", "base_wall"):
                o.data.materials.append(kinds[k])
            order = ["up", "wall", "base", "base_up", "base_wall"]
            for poly in o.data.polygons:
                pts = [co[i] for i in poly.vertices]
                n = (pts[1] - pts[0]).cross(pts[2] - pts[0])
                if n.length > 0:
                    n.normalize()
                low = min(p.z for p in pts) < 1.0 * PX + 1e-4
                up = n.z > 0.5
                key = ("base_" if low else "") + ("up" if up else "wall")
                poly.material_index = order.index(key)
        render(scene, Path(spec["out"]) / f"{view['name']}-kind.png")
        for o, (mats, idx) in zip(meshes, saved):
            o.data.materials.clear()
            for m in mats:
                o.data.materials.append(m)
            for poly, i in zip(o.data.polygons, idx):
                poly.material_index = i
    foot(meshes, originals, spec["out"])


def linear(c):
    c = c / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def foot(meshes, originals, out):
    """The model's section 1 px above its base, filled, seen from straight above: its footprint."""
    import bmesh
    for o, co in zip(meshes, originals):
        for v, p in zip(o.data.vertices, co):
            v.co = p
        bm = bmesh.new()
        bm.from_mesh(o.data)
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        res = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, PX), plane_no=(0, 0, 1), clear_outer=True)
        cut = [e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
        if cut:
            bmesh.ops.triangle_fill(bm, use_beauty=False, use_dissolve=False, edges=cut)
        bm.to_mesh(o.data)
        bm.free()
        o.data.update()
    render(bpy.context.scene, Path(out) / "foot.png")


def place(p, view, oblique):
    """A vertex (Blender, model frame) where the view sees it, on the ground plane, keeping its height."""
    if view["camera"] is None:
        return Vector((p.x, p.y, p.z))
    if oblique:
        return Vector((p.x, p.y + oblique * p.z, p.z))
    cx, cy, cz = view["camera"]  # three: x right, y up, z toward the screen's bottom
    y0 = -(view["screen_row"] - 92) * PX  # the pattern's centre, Blender Y (north)
    c = Vector((cx, -cz - y0, cy))  # the camera in the model's frame
    q = Vector((p.x, p.y, p.z))
    if c.z - q.z <= 1e-3:
        return q
    t = c.z / (c.z - q.z)
    g = c + (q - c) * t
    return Vector((g.x, g.y, p.z))


def render(scene, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


main()
