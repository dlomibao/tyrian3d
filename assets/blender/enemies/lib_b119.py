"""Helpers shared by batch b119's scripts (the two four-piece ground structures of newshb.shp).

Both assemblies are a row of four 2x2 pieces, 96 x 28 px in all. Geometry is given in assembly
pixel coordinates (column 0-95, row 0-27, pixel centres; fractions allowed, so a pixel's left
edge is c - 0.5), and the whole row is built once and cut with common.split_assembly.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

PX = 1 / 12  # one sprite pixel in units
W, H = 96, 28  # assembly size in pixels


def X(c):
    """Assembly pixel column (centre) to Blender X; the assembly's centre is the origin."""
    return (c + 0.5 - W / 2) / 12


def Y(r):
    """Assembly pixel row (centre) to Blender Y: sprite up is +Y."""
    return (H / 2 - (r + 0.5)) / 12


def _xy(p):
    return (X(p[0]), Y(p[1]))


def _ccw(pts):
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    return area > 0


def _tag(bm, before, mat, smooth):
    for f in set(bm.faces) - before:
        f.material_index = mat
        f.smooth = smooth


def stack(bm, rings, top_mat=0, side_mat=0, bottom_mat=None, smooth=False):
    """A solid through outlines of (col, row) points stacked in height: rings is a list of
    (outline, z) from the top down, every outline with the same number of points in the same
    winding. The top outline is capped with top_mat, the bottom one closed underneath. side_mat
    is a material index or a function (nx, ny) -> index of a side face's outward XY direction."""
    pts = [[_xy(p) for p in outline] for outline, _ in rings]
    if not _ccw(pts[-1]):
        pts = [p[::-1] for p in pts]
    vs = [[bm.verts.new((x, y, z)) for x, y in p] for p, (_, z) in zip(pts, rings)]
    f = bm.faces.new(vs[0])
    f.material_index, f.smooth = top_mat, False
    f = bm.faces.new(vs[-1][::-1])
    f.material_index, f.smooth = (top_mat if bottom_mat is None else bottom_mat), False
    n = len(vs[0])
    for k in range(len(vs) - 1):
        vt, vb, b = vs[k], vs[k + 1], pts[k + 1]
        for i in range(n):
            j = (i + 1) % n
            f = bm.faces.new((vb[i], vb[j], vt[j], vt[i]))
            dx, dy = b[j][0] - b[i][0], b[j][1] - b[i][1]
            ln = math.hypot(dx, dy) or 1.0
            f.material_index = side_mat(dy / ln, -dx / ln) if callable(side_mat) else side_mat
            f.smooth = smooth


def frustum(bm, top, bottom, z_top, z_bottom, top_mat=0, side_mat=0, bottom_mat=None, smooth=False):
    """A solid between two outlines of (col, row) points with the same number of points: `top`
    at z_top and `bottom` at z_bottom (both in the same winding)."""
    stack(bm, [(top, z_top), (bottom, z_bottom)], top_mat, side_mat, bottom_mat, smooth)


def blend(a, b, t):
    """Points t of the way from outline a to outline b."""
    return [(pa[0] + (pb[0] - pa[0]) * t, pa[1] + (pb[1] - pa[1]) * t) for pa, pb in zip(a, b)]


def plate(bm, outline, z0, z1, mat=0):
    """A flat plate from z0 to z1 with an outline of (col, row) points (use pixel edges)."""
    frustum(bm, outline, outline, z1, z0, top_mat=mat, side_mat=mat)


def box(bm, c0, r0, c1, r1, z0, z1, mat=0):
    """An axis-aligned box over pixel columns c0..c1 and rows r0..r1 (inclusive pixels)."""
    plate(bm, [(c0 - 0.5, r0 - 0.5), (c1 + 0.5, r0 - 0.5), (c1 + 0.5, r1 + 0.5), (c0 - 0.5, r1 + 0.5)],
          z0, z1, mat)


def ellipsoid(bm, col, row, z, rx_px, ry_px, rz, mat=0, segments=16, rings=8, z_min=None):
    """An ellipsoid; with z_min, vertices below it are flattened onto it (a dome on a base)."""
    before = set(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    for v in res["verts"]:
        co = Vector((X(col) + v.co.x * rx_px * PX, Y(row) + v.co.y * ry_px * PX, z + v.co.z * rz))
        if z_min is not None:
            co.z = max(co.z, z_min)
        v.co = co
    _tag(bm, before, mat, True)


def tube_y(bm, col, sections, sides=10, mat=0, smooth=True):
    """A loft down the sprite (along Y) on column `col`: sections are (row, half_width_px,
    half_height_units, z). Zero width and height make a point."""
    before = set(bm.faces)
    start = len(bm.verts)
    common.loft(bm, [(Y(r), w * PX, h, z) for r, w, h, z in sections], sides=sides, mat_index=mat)
    common.shift_x(bm, start, X(col))
    _tag(bm, before, mat, smooth)


def tube_x(bm, row, sections, sides=10, mat=0, smooth=True):
    """A loft across the sprite (along X) on row `row`: sections are (col, half_depth_px,
    half_height_units, z)."""
    before = set(bm.faces)
    start = len(bm.verts)
    common.loft(bm, [(X(c), w * PX, h, z) for c, w, h, z in sections], sides=sides, mat_index=mat)
    bm.verts.ensure_lookup_table()
    for v in bm.verts[start:]:  # loft runs along +Y with width on X: swap X and Y
        v.co.x, v.co.y = v.co.y, Y(row) + v.co.x
    _tag(bm, before, mat, smooth)


def mirror_cols(bm, axis_col, start_vert=0):
    """Add a mirror image, about the centre of pixel column axis_col (fractions allowed), of the
    geometry whose vertices were added since start_vert."""
    ax = X(axis_col)
    bm.verts.ensure_lookup_table()
    verts = set(bm.verts[start_vert:])
    faces = [f for f in bm.faces if all(v in verts for v in f.verts)]
    edges = list({e for f in faces for e in f.edges})
    dup = bmesh.ops.duplicate(bm, geom=list(verts) + edges + faces)["geom"]
    for v in (e for e in dup if isinstance(e, bmesh.types.BMVert)):
        v.co.x = 2 * ax - v.co.x
    bmesh.ops.reverse_faces(bm, faces=[e for e in dup if isinstance(e, bmesh.types.BMFace)])


def to_object(name, bm, mats, coll):
    """Like common.mesh_object, but keeps each face's own smooth/flat flag."""
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    return obj


def merged_sprite(root, pieces):
    """The first piece's sprite.json with the colours of every piece, so any index is valid."""
    data = common.load_sprite(root, pieces[0])
    for name in pieces[1:]:
        data["colors"].update(common.load_sprite(root, name)["colors"])
    return data


def layout(sprite, pieces):
    """(name, cx, cy) of each piece relative to the assembly's centre, for split_assembly."""
    entries = [e for e in sprite["assemblyLayout"] if e["model"] in pieces]
    cx0 = (min(e["cx"] for e in entries) + max(e["cx"] for e in entries)) / 2
    cy0 = (min(e["cy"] for e in entries) + max(e["cy"] for e in entries)) / 2
    return [(e["model"], e["cx"] - cx0, e["cy"] - cy0) for e in entries]


def composite_png(root, lay, out):
    """The whole row's sprite (first frames) as one image, padded to the 24:28 shape that
    render_preview expects for size 8 (96 x 112 px, the row in the middle)."""
    import numpy as np
    img = np.zeros((112, 96, 4), dtype=np.float32)
    for name, cx, cy in lay:
        data = common.load_sprite(root, name)
        frame = data["frames"][0]
        x0, y0 = int(cx + 48 - 12), int(cy + 56 - 14)
        for r, row in enumerate(frame["pixels"]):
            for c, v in enumerate(row):
                if v >= 0:
                    img[y0 + r, x0 + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", 96, 112, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def _split_open(obj, lay, suffix=""):
    """Cut `obj` into one open (unfilled) mesh per piece, centred on the piece."""
    import bmesh
    result = {}
    coll = obj.users_collection[0]
    for name, cx, cy in lay:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)
        hw, hh = 1.0, 14 / 12
        for co, no in (((x0 - hw, 0, 0), (-1, 0, 0)), ((x0 + hw, 0, 0), (1, 0, 0)),
                       ((0, y0 - hh, 0), (0, -1, 0)), ((0, y0 + hh, 0), (0, 1, 0))):
            geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
            bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(name + suffix)
        bm.to_mesh(me)
        bm.free()
        for mt in obj.data.materials:
            me.materials.append(mt)
        p = bpy.data.objects.new(name + suffix, me)
        coll.objects.link(p)
        result[name] = p
    return result


def _keep_normals(piece, source, cx, cy):
    piece.location = (cx / 12, -cy / 12, 0)
    bpy.context.view_layer.update()
    mod = piece.modifiers.new("keep_normals", "DATA_TRANSFER")
    mod.object = source
    mod.use_loop_data = True
    mod.data_types_loops = {"CUSTOM_NORMAL"}
    mod.loop_mapping = "POLYINTERP_NEAREST"
    mod.use_object_transform = True
    bpy.ops.object.select_all(action="DESELECT")
    piece.select_set(True)
    bpy.context.view_layer.objects.active = piece
    bpy.ops.object.modifier_apply(modifier=mod.name)
    piece.location = (0, 0, 0)
    bpy.context.view_layer.update()


def _sink_shell(shell, model, margin, reach):
    """Ink on the silhouette only (D90/D118/D185): drop each shell vertex `margin` under the lowest
    model top within `reach` of it, seen from above."""
    import math
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get()
    tree = BVHTree.FromObject(model, dg)
    for v in shell.data.vertices:
        w = shell.matrix_world @ v.co
        hit = tree.ray_cast(Vector((w.x, w.y, 5.0)), Vector((0, 0, -1)))
        if hit[0] is None:
            continue
        zt = hit[0].z
        for k in range(12):
            a = 2 * math.pi * k / 12
            for rad in (0.35 * reach, 0.7 * reach, reach):
                h = tree.ray_cast(Vector((w.x + rad * math.cos(a), w.y + rad * math.sin(a), 5.0)), Vector((0, 0, -1)))
                if h[0] is not None:
                    zt = min(zt, h[0].z)
        zt -= margin
        if w.z > zt:
            v.co = shell.matrix_world.inverted() @ Vector((w.x, w.y, zt))
    shell.data.update()


def _shell_of_groups(pre, coll, groups):
    """common.outline_shell keeps only the largest island of its voxel remesh, so a row of separate
    bodies (newshb-2's two pods) gets one shell per group of columns (x ranges in units), joined."""
    import bmesh
    if not groups:
        return common.outline_shell(pre, coll, voxel=0.016, faces=6000, smooth=6, inside=0.004)
    shells = []
    for x0, x1 in groups:
        part = pre.copy()
        part.data = pre.data.copy()
        coll.objects.link(part)
        bm = bmesh.new()
        bm.from_mesh(part.data)
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not x0 <= v.co.x <= x1], context="VERTS")
        bm.to_mesh(part.data)
        bm.free()
        shells.append(common.outline_shell(part, coll, voxel=0.016, faces=6000 // len(groups), smooth=6, inside=0.004))
        bpy.data.objects.remove(part, do_unlink=True)
    bm = bmesh.new()
    for sh in shells:
        bm.from_mesh(sh.data)
    bm.to_mesh(shells[0].data)
    bm.free()
    for sh in shells[1:]:
        bpy.data.objects.remove(sh, do_unlink=True)
    return shells[0]


def export_assembly(root, obj, sprite, pieces, textured=None, tag="b119", shell_groups=None):
    """D65 finish: cull faces nothing can see, weighted normals (faired shading), the AO/roughness
    bake (bake_maps, into the material slots `textured`; "--no-bake" skips it), an outline shell
    from a sealed pre-cull copy (D90/D118, ink on the silhouette only), cut into the pieces, each
    exported with its shell and sprites. With --preview <png>, render the whole row and each piece."""
    import usp_talon as T
    lay = layout(sprite, pieces)
    coll = obj.users_collection[0]
    pre = obj.copy()
    pre.data = obj.data.copy()
    coll.objects.link(pre)
    T.cull_hidden(obj, grid=4, ndirs=40)
    bpy.context.view_layer.update()
    wn = obj.modifiers.new("weighted", "WEIGHTED_NORMAL")
    wn.keep_sharp = True
    wn.weight = 50
    common._apply_modifiers(obj)
    fmt = "AUTO"
    if textured and "--no-bake" not in sys.argv:
        import tempfile
        bake_maps(obj, tempfile.mkdtemp(prefix=f"{tag}_bake_"), textured, tag)
        fmt = "WEBP"
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{obj.name}: {tris} triangles after cull")
    sh = _shell_of_groups(pre, coll, shell_groups)
    _sink_shell(sh, obj, 0.02, 0.06)
    bpy.data.objects.remove(pre, do_unlink=True)
    parts = _split_open(obj, lay)
    shells = _split_open(sh, lay, "_outline")
    for name, cx, cy in lay:
        _keep_normals(parts[name], obj, cx, cy)
        s = shells[name]
        s["tyrian_outline"] = True
        s.data.materials.clear()
        s.data.materials.append(bpy.data.materials["outline_shell"])
        s.data.shade_smooth()
    for name in pieces:
        data = common.load_sprite(root, name)
        common.export_sprite_model(root, [parts[name], shells[name]], f"enemies/{name}", data["sprites"],
                                   image_format=fmt)
    if "--preview" in sys.argv:
        import tempfile
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        ref = composite_png(root, lay, Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), str(ref), size=8, view_px=480)
        for name in pieces:
            data = common.load_sprite(root, name)
            img = root / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([parts[name]], str(out.parent / f"{name}.png"), img, size=2)
    return parts


# --- AO/roughness bake (usp_talon.bake_maps with the material slots passed in, D53/D65) -------------

def bake_maps(obj, out_dir, textured, tag, size=1024, samples=64):
    """Smart UV, Cycles bake of an occlusion/edge colour multiplier and a roughness/metallic map,
    wired into the palette materials of the slots `textured` (Base Color = map x palette colour,
    G roughness, B metallic), as usp_talon.bake_maps. Glow materials stay plain."""
    import math as _m
    scene = bpy.context.scene
    try:
        scene.render.engine = "CYCLES"
    except TypeError:
        pass
    scene.cycles.samples = samples
    scene.cycles.device = "CPU"
    me = obj.data
    uv = me.uv_layers.new(name="bake")
    me.uv_layers.active = uv
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=_m.radians(55), island_margin=0.006, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.006)  # wide enough that no island bleeds into its neighbour
    bpy.ops.object.mode_set(mode="OBJECT")
    col_img = bpy.data.images.new(f"{tag}_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new(f"{tag}_rm", size // 2, size // 2, alpha=False)
    rm_img.colorspace_settings.name = "Non-Color"
    mats = list(dict.fromkeys(me.materials))  # slots may share one material: each once
    saved = {}
    for m in mats:
        out = next(n for n in m.node_tree.nodes if n.type == "OUTPUT_MATERIAL")
        saved[m.name] = out.inputs["Surface"].links[0].from_socket if out.inputs["Surface"].links else None

    def bake_shader(m, mode):
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        rough = bsdf.inputs["Roughness"].default_value
        metal = bsdf.inputs["Metallic"].default_value
        tmp = []

        def node(kind):
            n = nt.nodes.new(kind)
            tmp.append(n)
            return n

        def math_(op, a, bb=None):
            n = node("ShaderNodeMath")
            n.operation = op
            for k, v in enumerate((a, bb)):
                if v is None:
                    continue
                if isinstance(v, (int, float)):
                    n.inputs[k].default_value = v
                else:
                    nt.links.new(v, n.inputs[k])
            return n.outputs[0]
        ao_s = node("ShaderNodeAmbientOcclusion")
        ao_s.samples = 24
        ao_s.inputs["Distance"].default_value = 0.04
        ao_l = node("ShaderNodeAmbientOcclusion")
        ao_l.samples = 24
        ao_l.inputs["Distance"].default_value = 0.25
        bev = node("ShaderNodeBevel")
        bev.samples = 8
        bev.inputs["Radius"].default_value = 0.006
        geo = node("ShaderNodeNewGeometry")
        dot = node("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        nt.links.new(bev.outputs["Normal"], dot.inputs[0])
        nt.links.new(geo.outputs["True Normal"], dot.inputs[1])
        edge = math_("MINIMUM", math_("MULTIPLY", math_("SUBTRACT", 1.0, dot.outputs["Value"]), 8.0), 1.0)
        occl = math_("MULTIPLY", math_("POWER", ao_s.outputs["AO"], 0.8),
                     math_("ADD", 0.65, math_("MULTIPLY", ao_l.outputs["AO"], 0.35)))
        em = node("ShaderNodeEmission")
        if mode == "colour":
            v = math_("MINIMUM", math_("ADD", math_("ADD", 0.48, math_("MULTIPLY", occl, 0.62)),
                                       math_("MULTIPLY", edge, 0.2)), 1.0)
            tint = node("ShaderNodeCombineColor")
            for k in range(3):
                nt.links.new(v, tint.inputs[k])
            nt.links.new(tint.outputs[0], em.inputs["Color"])
        else:
            r = math_("ADD", rough, math_("SUBTRACT", math_("MULTIPLY", math_("SUBTRACT", 1.0, occl), 0.3),
                                          math_("MULTIPLY", edge, 0.16)))
            r = math_("MAXIMUM", math_("MINIMUM", r, 1.0), 0.05)
            comb = node("ShaderNodeCombineColor")
            comb.inputs[0].default_value = 1.0
            nt.links.new(r, comb.inputs[1])
            comb.inputs[2].default_value = metal
            nt.links.new(comb.outputs[0], em.inputs["Color"])
        out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
        nt.links.new(em.outputs[0], out.inputs["Surface"])
        tgt = node("ShaderNodeTexImage")
        tgt.image = col_img if mode == "colour" else rm_img
        uvn = node("ShaderNodeUVMap")
        uvn.uv_map = "bake"
        nt.links.new(uvn.outputs["UV"], tgt.inputs["Vector"])
        nt.nodes.active = tgt
        return tmp

    for mode, img in (("colour", col_img), ("rm", rm_img)):
        tmps = {m.name: bake_shader(m, mode) for m in mats}
        bpy.ops.object.bake(type="EMIT", margin=6, use_clear=True)
        for m in mats:
            nt = m.node_tree
            for n in tmps[m.name]:
                nt.nodes.remove(n)
            out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
            if saved[m.name] is not None:
                nt.links.new(saved[m.name], out.inputs["Surface"])
        img.filepath_raw = str(Path(out_dir) / f"{img.name}.png")
        img.file_format = "PNG"
        img.save()
    for m in dict.fromkeys(me.materials[i] for i in textured):
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        uvn = nt.nodes.new("ShaderNodeUVMap")
        uvn.uv_map = "bake"
        ct = nt.nodes.new("ShaderNodeTexImage")
        ct.image = col_img
        nt.links.new(uvn.outputs["UV"], ct.inputs["Vector"])
        mul = nt.nodes.new("ShaderNodeMix")
        mul.data_type = "RGBA"
        mul.blend_type = "MULTIPLY"
        mul.inputs[0].default_value = 1.0
        nt.links.new(ct.outputs["Color"], mul.inputs[6])
        mul.inputs[7].default_value = tuple(bsdf.inputs["Base Color"].default_value)
        nt.links.new(mul.outputs[2], bsdf.inputs["Base Color"])
        rt = nt.nodes.new("ShaderNodeTexImage")
        rt.image = rm_img
        nt.links.new(uvn.outputs["UV"], rt.inputs["Vector"])
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(rt.outputs["Color"], sep.inputs[0])
        nt.links.new(sep.outputs[1], bsdf.inputs["Roughness"])
        nt.links.new(sep.outputs[2], bsdf.inputs["Metallic"])


# --- D65 hard-surface helpers (pixel EDGE coordinates: c = 10 is the left edge of column 10) --------

def XE(c):
    return (c - W / 2) / 12


def YE(r):
    return (H / 2 - r) / 12


class M:
    """A bmesh with a material per face."""

    def __init__(self):
        self.bm = bmesh.new()

    def face(self, verts, mat):
        try:
            f = self.bm.faces.new(verts)
        except ValueError:
            return None
        f.material_index = mat
        return f

    def nv(self, p):
        return self.bm.verts.new(p)

    def mark(self):
        return len(self.bm.verts)

    def mirror_since(self, n, axis_edge):
        """Mirror the geometry added since vertex n about the column EDGE axis_edge."""
        bm = self.bm
        bm.verts.ensure_lookup_table()
        verts = bm.verts[n:]
        faces = list({f for v in verts for f in v.link_faces})
        edges = list({e for v in verts for e in v.link_edges})
        dup = bmesh.ops.duplicate(bm, geom=list(verts) + edges + faces)["geom"]
        ax = XE(axis_edge)
        for v in (e for e in dup if isinstance(e, bmesh.types.BMVert)):
            v.co.x = 2 * ax - v.co.x
        bmesh.ops.reverse_faces(bm, faces=[e for e in dup if isinstance(e, bmesh.types.BMFace)])

    def to_object(self, name, mats, coll, sharp_deg=35):
        bm = self.bm
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        for mt in mats:
            me.materials.append(mt)
        obj = bpy.data.objects.new(name, me)
        coll.objects.link(obj)
        me.shade_smooth()
        me.set_sharp_from_angle(angle=math.radians(sharp_deg))
        return obj


def rings_faces(m, rings, mat, cap0=True, cap1=True, mats=None):
    for i, (a, b) in enumerate(zip(rings, rings[1:])):
        n = len(a)
        mt = mats[i] if mats else mat
        for k in range(n):
            j = (k + 1) % n
            m.face((a[k], a[j], b[j], b[k]), mt)
    if cap0:
        m.face(list(reversed(rings[0])), mats[0] if mats else mat)
    if cap1:
        m.face(rings[-1], mats[-1] if mats else mat)


def area2(pts):
    return sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))


def inset(pts, d):
    """Offset a CCW (x, y) polygon inward by d (miter, clamped)."""
    n = len(pts)
    out = []
    for i in range(n):
        p0, p1, p2 = Vector(pts[i - 1]), Vector(pts[i]), Vector(pts[(i + 1) % n])
        e0 = (p1 - p0).normalized()
        e1 = (p2 - p1).normalized()
        n0 = Vector((-e0.y, e0.x))
        n1 = Vector((-e1.y, e1.x))
        b = n0 + n1
        if b.length < 1e-6:
            b = n0
        b.normalize()
        cs = max(0.4, b.dot(n1))
        q = p1 + b * (d / cs)
        out.append((q.x, q.y))
    return out


def dedupe(pts, eps=1e-4):
    out = []
    for p in pts:
        if not out or (abs(p[0] - out[-1][0]) > eps or abs(p[1] - out[-1][1]) > eps):
            out.append(p)
    if len(out) > 2 and abs(out[0][0] - out[-1][0]) < eps and abs(out[0][1] - out[-1][1]) < eps:
        out.pop()
    return out


def slab(m, outline_px, z0, z1, mat, ch=0.03, chb=0.0, top_mat=None, z1s=None):
    """A chamfered block over an outline of (col, row) edges: sides z0..z1 - ch, a 45 degree chamfer
    to a top inset by ch (units); chb insets the bottom. z1s: per-point top heights."""
    pts = dedupe([(XE(c), YE(r)) for c, r in outline_px])
    tops = list(z1s) if z1s else [z1] * len(pts)
    if area2(pts) < 0:
        pts, tops = pts[::-1], tops[::-1]
    rings = []
    if chb > 0:
        rings.append([m.nv((x, y, z0)) for x, y in inset(pts, chb)])
        rings.append([m.nv((x, y, z0 + chb * 0.8)) for x, y in pts])
    else:
        rings.append([m.nv((x, y, z0)) for x, y in pts])
    if ch > 0:
        rings.append([m.nv((x, y, t - ch)) for (x, y), t in zip(pts, tops)])
        rings.append([m.nv((x, y, t)) for (x, y), t in zip(inset(pts, ch), tops)])
    else:
        rings.append([m.nv((x, y, t)) for (x, y), t in zip(pts, tops)])
    rings_faces(m, rings, mat, cap0=False, cap1=False)
    m.face(list(reversed(rings[0])), mat)
    m.face(rings[-1], top_mat if top_mat is not None else mat)


def chbox(m, c0, r0, c1, r1, z0, z1, mat, ch=0.3, chz=None, top_mat=None):
    """A box over edges c0..c1, r0..r1 with chamfered vertical corners (ch px) and top edges."""
    chz = ch * PX if chz is None else chz
    o = [(c0 + ch, r0), (c1 - ch, r0), (c1, r0 + ch), (c1, r1 - ch), (c1 - ch, r1), (c0 + ch, r1),
         (c0, r1 - ch), (c0, r0 + ch)]
    slab(m, o, z0, z1, mat, ch=chz, top_mat=top_mat)


def dome_slab(m, outline_px, z0, z1, rise, mat, steps=4, shrink=0.6):
    """A lens: sides z0..z1, then a rounded top rising `rise` over `steps` inset rings."""
    pts = dedupe([(XE(c), YE(r)) for c, r in outline_px])
    if area2(pts) < 0:
        pts = pts[::-1]
    rings = [[m.nv((x, y, z0)) for x, y in pts], [m.nv((x, y, z1)) for x, y in pts]]
    for k in range(1, steps + 1):
        a = k / steps * math.pi / 2
        d = shrink * PX * (1 - math.cos(a)) * 2.2
        rings.append([m.nv((x, y, z1 + rise * math.sin(a))) for x, y in inset(pts, d)])
    rings_faces(m, rings, mat, cap0=True, cap1=True)


def lathe_y(m, col, prof, mat, sides=16, cap0=True, cap1=True, mats=None):
    """A solid of revolution about an axis down the sprite at column EDGE col: prof = [(row,
    radius_px, axis_z)] (radius 0 = a point)."""
    rings = []
    for r, rad, z in prof:
        rings.append([m.nv((XE(col) + math.cos(2 * math.pi * (k + 0.5) / sides) * rad * PX, YE(r),
                            z + math.sin(2 * math.pi * (k + 0.5) / sides) * rad * PX)) for k in range(sides)])
    rings_faces(m, rings, mat, cap0, cap1, mats=mats)


def lathe_z(m, col, row, prof, mat, sides=16, cap0=True, cap1=True, mats=None):
    """A solid of revolution about a vertical axis at (col, row) edges: prof = [(z, radius_px)]."""
    rings = []
    for z, rad in prof:
        rings.append([m.nv((XE(col) + math.cos(2 * math.pi * (k + 0.5) / sides) * rad * PX,
                            YE(row) + math.sin(2 * math.pi * (k + 0.5) / sides) * rad * PX, z)) for k in range(sides)])
    rings_faces(m, rings, mat, cap0, cap1, mats=mats)


def pchip(xs, ys, x):
    """Monotone cubic (Fritsch-Carlson) interpolation: no overshoot between stations."""
    n = len(xs)
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    h = [xs[i + 1] - xs[i] for i in range(n - 1)]
    d = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]
    t = [0.0] * n
    t[0], t[-1] = d[0], d[-1]
    for i in range(1, n - 1):
        if d[i - 1] * d[i] <= 0:
            t[i] = 0.0
        else:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            t[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
    i = max(k for k in range(n - 1) if xs[k] <= x)
    s = (x - xs[i]) / h[i]
    h00, h10 = 2 * s ** 3 - 3 * s ** 2 + 1, s ** 3 - 2 * s ** 2 + s
    h01, h11 = -2 * s ** 3 + 3 * s ** 2, s ** 3 - s ** 2
    return h00 * ys[i] + h10 * h[i] * t[i] + h01 * ys[i + 1] + h11 * h[i] * t[i + 1]
