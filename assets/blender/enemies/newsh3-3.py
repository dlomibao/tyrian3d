"""newsh3-3, design A: the dressed-sandstone capstone pyramid on top of SURFACE's stepped pyramids
(newsh3.shp 3/4/5, 12x14 px, size 1; episode 4, level 4.2).

What it is. Not a free-standing companion pyramid: in every one of its 37 spawns it is linked rigid
with the four pieces of the stepped pyramid (assembly-newsh3-191) at their dx -10/+14, dy +5/+33, i.e.
its 12x14 box is cols 16-28, rows 2-16 of that 48x56 tile, exactly the pyramid's summit. The pyramid's
own sprite draws the same cap there (identical pixels), and D195's pyramid ends in a flat platform
(cols 16-28, rows 3.4-16.2, top 0.855) for it: D181's cover rule raises this model onto that platform.
So this is the pointed capstone pyramid (a pyramidion on a footing course) of a temple-pyramid.

Read from the sprite (light from the upper left, the game's oblique view, D195's lean):
- The point leans to the top of the screen: a pyramid whose apex stands over its north edge, so the
  top view is the base rectangle (rows 2-13, full width) plus a north overhang narrowing to the point
  (row 1 cols 2-9, row 0 cols 4-7). Faces: the lit west face a long triangle down the left (25), the
  south face the big triangle in the middle (20), the east face a strip down the right (22), the north
  face hangs over and is unseen from above (19).
- The 27 line down the left (row 3 col 4 ... row 9 col 1) is the SW arris catching the light: a
  chamfered ridge, not a strip of paint. Row 1's 27|22 is the capstone (pyramidion), lit west, shaded
  east, set off by a joint.
- Col 0 (21/22), col 11 (20/19/17) and row 13 (19) are the battered sides of a low footing course; row
  2 cols 0-1 (19) its north edge. The brightening frames 4/5 lift each colour two / four shades
  (palette_material frames=); the east footing and the ring stay dark in all three.
- Courses: dressed stone in courses, V joints every COURSE units (as D195's terraces), lit by the AO
  bake only.

Contract: one model, every frame; pal_<index> materials; the outline shell from a sealed copy without
joints (D51/D90), sunk under the top surfaces so ink stays on the silhouette; AO/roughness bake from
the model (D50, "bake": "model"), no concept projection.

Run: blender -b --factory-startup --python assets/blender/enemies/newsh3-3.py [-- --nobake]
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

WT = common.repo_root(__file__)

NAME = "newsh3-3"
TAG = "n3_3"
PX = 1 / 12
W, H = 12, 14


def X(u):
    return (u - W / 2) * PX


def Y(v):
    return (H / 2 - v) * PX


def P(u, v, z):
    return Vector((X(u), Y(v), z))


# Footing course (pixel edges at the foot, its top inset by the batter) and the pyramid on it.
FOOT = dict(w=0.0, e=12.0, n=2.0, s=14.0)
FOOT_Z = 0.05
FOOT_BATTER = dict(w=0.85, e=0.85, n=0.3, s=0.9)
SET = 0.12            # px the pyramid's foot is set back from the footing's top edge (a small ledge)
APEX = (6.0, -0.45)   # the point (column, row edges): over the north edge, as the sprite leans
ZT = 0.68             # apex height over the footing's foot
CAP_T = 0.78          # the capstone starts at this fraction of the pyramid's height
CHAMFER = 0.42        # px across each arris at the foot (shrinks toward the point)
COURSE = 0.075        # masonry course height (units): a V joint every course
GROOVE = 0.10         # joint depth (px)
JOINT = 0.006         # half the joint's height (units)


def materials(sprite):
    def pal(i, roughness, spec=0.28, bright=True):
        frames = {4: i + 2, 5: i + 4} if bright else None
        m = common.palette_material(sprite, i, f"{TAG}_{i}_{int(roughness * 100)}{'' if bright else '_fixed'}", metallic=0.0,
                                    roughness=roughness, frames=frames)
        bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        if "Specular IOR Level" in bsdf.inputs:
            bsdf.inputs["Specular IOR Level"].default_value = spec
        return m

    spec = [  # key, palette index, roughness, brightens with frames 4/5
        ("w", 25, 0.78, True), ("sw", 27, 0.72, True), ("s", 20, 0.9, True), ("se", 23, 0.8, True),
        ("e", 22, 0.84, True), ("ne", 21, 0.86, True), ("n", 19, 0.9, False), ("nw", 21, 0.86, True),
        ("cap_w", 27, 0.72, True), ("cap_e", 22, 0.8, True), ("cap_s", 23, 0.8, True),
        ("foot_w", 21, 0.86, True), ("foot_s", 19, 0.9, True), ("foot_e", 19, 0.9, False),
        ("foot_n", 19, 0.9, False), ("foot_top", 21, 0.86, True),
    ]
    mats, M, seen = [], {}, {}
    for key, idx, rough, bright in spec:
        sig = (idx, rough, bright)
        if sig not in seen:
            seen[sig] = len(mats)
            mats.append(pal(idx, rough, bright=bright))
        M[key] = seen[sig]
    return mats, M


SEG = ["n", "nw", "w", "sw", "s", "se", "e", "ne"]


def ring_pts(w, e, n, s, z, c):
    """A chamfered rectangle (pixel edges) at height z, 8 points counter-clockwise seen from above,
    starting at the north edge's east end: segments N, NW, W, SW, S, SE, E, NE follow."""
    c = max(min(c, (e - w) * 0.45, (s - n) * 0.45), 1e-4)
    return [P(e - c, n, z), P(w + c, n, z), P(w, n + c, z), P(w, s - c, z),
            P(w + c, s, z), P(e - c, s, z), P(e, s - c, z), P(e, n + c, z)]


def loft(bm, rings, bands, cap_bottom=None, cap_top=None):
    vs = [[bm.verts.new(p) for p in r] for r in rings]
    for k, (a, b) in enumerate(zip(vs, vs[1:])):
        for i in range(8):
            f = bm.faces.new((a[i], a[(i + 1) % 8], b[(i + 1) % 8], b[i]))
            f.material_index = bands[k][i]
    if cap_bottom is not None:
        f = bm.faces.new(list(reversed(vs[0])))
        f.material_index = cap_bottom
    if cap_top is not None:
        f = bm.faces.new(vs[-1])
        f.material_index = cap_top
    return vs


def footing(bm, M):
    """The low battered footing course under the pyramid (rows 2-14), its top a narrow ledge."""
    f, b = FOOT, FOOT_BATTER
    c = 0.3
    bot = ring_pts(f["w"], f["e"], f["n"], f["s"], 0.0, c)
    top_edges = (f["w"] + b["w"], f["e"] - b["e"], f["n"] + b["n"], f["s"] - b["s"])
    mid = ring_pts(*top_edges, FOOT_Z - 0.008, c * 0.8)
    lip = ring_pts(top_edges[0] + 0.12, top_edges[1] - 0.12, top_edges[2] + 0.08, top_edges[3] - 0.12, FOOT_Z, c * 0.7)
    wall = {"n": M["foot_n"], "nw": M["foot_n"], "w": M["foot_w"], "sw": M["foot_s"], "s": M["foot_s"],
            "se": M["foot_s"], "e": M["foot_e"], "ne": M["foot_e"]}
    band = [wall[s] for s in SEG]
    loft(bm, [bot, mid, lip], [band, [M["foot_top"]] * 8], cap_bottom=M["foot_n"], cap_top=M["foot_top"])
    return top_edges


def pyramid_edges(base, t):
    """(w, e, n, s) of the pyramid's horizontal section at fraction t of its height: every face a plane
    from the foot rectangle to the apex."""
    w, e, n, s = base
    ax, ay = APEX
    return (w + (ax - w) * t, e + (ax - e) * t, n + (ay - n) * t, s + (ay - s) * t)


def pyramid_base(top_edges):
    w0, e0, n0, s0 = top_edges
    return (w0 + SET + 0.12, e0 - SET - 0.12, n0 + SET, s0 - SET - 0.12)


def pyramid(bm, M, top_edges, joints=True):
    base = pyramid_base(top_edges)
    z0 = FOOT_Z
    h = ZT - z0
    face = {k: M[k] for k in SEG}
    band = [face[s] for s in SEG]
    zc = z0 + h * CAP_T
    seq = [(z0, 0.0), (zc - JOINT * 1.6, 0.0)]
    if joints:
        k = 1
        while z0 + k * COURSE < zc - 0.03:
            g = z0 + k * COURSE
            seq += [(g - JOINT, 0.0), (g, GROOVE), (g + JOINT, 0.0)]
            k += 1
    seq.sort()
    rings = []
    for z, ins in seq:
        t = (z - z0) / h
        we, ee, ne, se = pyramid_edges(base, t)
        c = CHAMFER * (1 - t) + 0.05
        rings.append(ring_pts(we + ins, ee - ins, ne + ins, se - ins, z, c))
    # The capstone joint (a V joint) and the capstone: one continuous loft up to the point.
    cap_face = {"n": M["n"], "nw": M["cap_w"], "w": M["cap_w"], "sw": M["cap_w"], "s": M["cap_s"],
                "se": M["cap_e"], "e": M["cap_e"], "ne": M["cap_e"]}
    cband = [cap_face[s] for s in SEG]
    g = GROOVE * 1.3 if joints else 0.0
    bands = [band] * (len(rings) - 1)
    for z, ins, b in ((zc, g, band), (zc + JOINT * 2.2, 0.0, cband)):
        t = (z - z0) / h
        we, ee, ne, se = pyramid_edges(base, t)
        c = CHAMFER * (1 - t) + 0.05
        rings.append(ring_pts(we + ins, ee - ins, ne + ins, se - ins, z, c))
        bands.append(b)
    vs = loft(bm, rings, bands, cap_bottom=M["n"])
    top = vs[-1]
    apex = bm.verts.new(P(APEX[0], APEX[1], ZT))
    for i in range(8):
        f = bm.faces.new((top[i], top[(i + 1) % 8], apex))
        f.material_index = cband[i]


def ink_shell(coll, top_edges, inset=0.14, sink=0.035):
    """The outline shell (D51): a sealed, smooth copy of the pyramid alone, `inset` px inside its faces
    and its apex `sink`/3 lower, reaching `sink` units under the footing's top. The cap stands on the
    stepped pyramid's platform, so its foot is no silhouette: no ink round the footing (the sprite has
    none; a voxel shell drew a black frame there and scribbles over the faces in game), ink only where
    the pyramid stands against what is behind it."""
    base = pyramid_base(top_edges)
    z0, h = FOOT_Z, ZT - FOOT_Z
    bm = bmesh.new()
    rings = []
    for z in (z0 - sink, z0 + h * 0.25, z0 + h * 0.5, z0 + h * 0.75, z0 + h * 0.92):
        t = (z - z0) / h
        we, ee, ne, se = pyramid_edges(base, t)
        c = CHAMFER * (1 - t) + 0.05
        rings.append(ring_pts(we + inset, ee - inset, ne + inset, se - inset, z, c))
    band = [0] * 8
    vs = loft(bm, rings, [band] * (len(rings) - 1), cap_bottom=0)
    apex = bm.verts.new(P(APEX[0], APEX[1] + inset, ZT - sink / 3))
    for i in range(8):
        bm.faces.new((vs[-1][i], vs[-1][(i + 1) % 8], apex))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(f"{NAME}_outline")
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    me.materials.append(common.material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0))
    shell = bpy.data.objects.new(f"{NAME}_outline", me)
    coll.objects.link(shell)
    shell["tyrian_outline"] = True
    return shell


def build(coll, joints=True, name=NAME, sprite=None):
    mats, M = materials(sprite)
    bm = bmesh.new()
    top_edges = footing(bm, M)
    pyramid(bm, M, top_edges, joints)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    for p in me.polygons:
        p.use_smooth = True
    me.set_sharp_from_angle(angle=math.radians(30))
    return obj


# --- helpers copied from D195's assembly-newsh3-191 (no shared file edited) -----------------------

def bake_maps(obj, tag, size=512, samples=48):
    scene = bpy.context.scene
    try:
        scene.render.engine = "CYCLES"
    except TypeError:
        pass
    scene.cycles.samples = samples
    scene.cycles.device = "CPU"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for dev in prefs.devices:
            dev.use = True
        if any(d.type == "METAL" for d in prefs.devices):
            scene.cycles.device = "GPU"
    except Exception as err:  # noqa: BLE001
        print("no GPU bake", err)
    me = obj.data
    uv = me.uv_layers.new(name="bake")
    me.uv_layers.active = uv
    bpy.context.view_layer.update()
    for o in bpy.context.scene.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.004, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.003)
    bpy.ops.object.mode_set(mode="OBJECT")
    col_img = bpy.data.images.new(f"{tag}_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new(f"{tag}_rm", size // 2, size // 2, alpha=False)
    rm_img.colorspace_settings.name = "Non-Color"
    mats = list(me.materials)
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

        def math_(op, a, b=None):
            n = node("ShaderNodeMath")
            n.operation = op
            for k, v in enumerate((a, b)):
                if v is None:
                    continue
                if isinstance(v, (int, float)):
                    n.inputs[k].default_value = v
                else:
                    nt.links.new(v, n.inputs[k])
            return n.outputs[0]
        ao_s = node("ShaderNodeAmbientOcclusion")
        ao_s.samples = 24
        ao_s.inputs["Distance"].default_value = 0.02
        ao_l = node("ShaderNodeAmbientOcclusion")
        ao_l.samples = 24
        ao_l.inputs["Distance"].default_value = 0.1
        bev = node("ShaderNodeBevel")
        bev.samples = 8
        bev.inputs["Radius"].default_value = 0.003
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
            v = math_("MINIMUM", math_("ADD", math_("ADD", 0.5, math_("MULTIPLY", occl, 0.6)),
                                       math_("MULTIPLY", edge, 0.18)), 1.0)
            comb = node("ShaderNodeCombineColor")
            for k in range(3):
                nt.links.new(v, comb.inputs[k])
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
        img.pack()

    for m in mats:
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


def sink_shell(shell, model, margin, reach):
    """Keep the outline shell under the model's top surface (D90/D118: ink on the silhouette only); x and
    y are untouched, so the silhouette (and the ink round it) stays."""
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get()
    tree = BVHTree.FromObject(model, dg)
    mw = shell.matrix_world
    inv = mw.inverted()
    for v in shell.data.vertices:
        w = mw @ v.co
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
            v.co = inv @ Vector((w.x, w.y, zt))
    shell.data.update()


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    sprite = common.load_sprite(WT, NAME)
    coll = common.reset_collection(NAME)
    obj = build(coll, sprite=sprite)
    f, b = FOOT, FOOT_BATTER
    shell = ink_shell(coll, (f["w"] + b["w"], f["e"] - b["e"], f["n"] + b["n"], f["s"] - b["s"]))
    assert len(shell.data.vertices) > 0
    obj.data.calc_loop_triangles()
    print("TRIS", len(obj.data.loop_triangles), "shell verts", len(shell.data.vertices))
    fmt = "AUTO"
    if "--nobake" not in argv:
        shell.hide_render = True
        bake_maps(obj, TAG)
        shell.hide_render = False
        fmt = "WEBP"
    sprites = sprite["sprites"]
    common.export_sprite_model(WT, [obj, shell], f"enemies/{NAME}", sprites, image_format=fmt)


if __name__ == "__main__":
    main()
