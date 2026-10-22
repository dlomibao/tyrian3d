"""Helpers shared by the asset build scripts: scene reset, materials, simple mesh builders, export."""

import math
from pathlib import Path

import bmesh
import bpy


def repo_root(script_file):
    """The repository root, from a script in assets/blender/."""
    return Path(script_file).resolve().parents[2]


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


def mesh_object(name, bm, materials, collection):
    """Turn a bmesh into a flat-shaded object with the given material slots."""
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = False
    for mat in materials:
        mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj


def export_glb(objects, path):
    """Export only `objects` to a .glb (Y-up, modifiers applied)."""
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
    )
    return path
