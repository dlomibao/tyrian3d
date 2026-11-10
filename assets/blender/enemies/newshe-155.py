"""newshe-155: a lava egg cluster, seven glossy molten balls heaped together.

Reading of the sprite (24x28, newshe.shp 155-165): seven round balls (two big ones on the left, one
back right, a small one on the right, the crowning middle one, a small one beside the front, the
front tip), lit from the upper right: the 122-124 spots are sheen on glossy round shells, the
113-115 pixels the shadowed lower flanks, the crevices between the balls and (frame 155 only) the
ink ring. The six frames are the same drawing heated up the red-yellow ramp; the body colour steps
117 -> 119 -> 120 -> 121 -> 122 -> 124 (each frame's median).

Two bodies (D17 frame parts), because the drawing's edge changes with the heat: on frame 155 the
1 px edge is ink (114, luma < 26), so the model stands at its inner edge (D74); on 157-165 the same
edge is drawn in the glow colour (116-122, no ink: OUTLINE-BORDER.md rule 2), so the hot body
stands at the outer edge. Same ball centres, the hot balls 0.5-0.8 px bigger in radius, so the
heap swells a hair as it heats instead of jumping. Each has its own outline shell on its frames.

Shape: each ball is a near-sphere (plan axis ratio <= 1.12), its plan fitted to the sprite's mask
(tyrian-scratch/e1-enemies-2/newshe-155/B/fit.py: 7 ellipses, union IoU); the middle ball rides
higher (the heap), the rest sit low, each closed below its girth by a flatter half resting on the
ground. The balls intersect in sharp creases (the seams), which the AO bake darkens: the sprite's
dark 113-115 gaps. (The earlier cooled-lava crust under the heap could not be seen from any
view and is gone.) Underside: the balls' flattened bottoms, nothing more.

Run: tools/build-models.sh assets/blender/enemies/newshe-155.py   ([-- --no-bake] skips the AO/roughness bake)
Exports public/models/enemies/newshe-155.glb and src/render/spriteModels/newshe-155.json.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy

ROOT = Path(__file__).resolve().parents[3]
WT = ROOT
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

HERE = Path("/Users/dlomibao/projects/tyrian-scratch/e1-enemies-2/newshe-155/final")
NAME = "newshe-155"
MODEL = f"enemies/{NAME}"
U = 1 / 12
GW, GH = 24, 28

# Balls: (centre col, centre row in px (pixel c spans c..c+1), radius r px, plan axis ratio e (the
# axis along `ang` is r*e, the other r/e), ang rad in the image (y down), height factor, lift px).
# Frame 155 fits the inner mask (ink edge); the hot frames' radii fit the outer mask.
COLD = [
    (7.571, 8.732, 5.996, 1.114, 0.504),    # big, back left
    (17.713, 7.490, 4.380, 0.916, 0.606),   # back right
    (20.030, 12.945, 2.650, 1.113, 0.006),  # small, right
    (6.039, 18.100, 5.007, 1.037, -0.555),  # big, front left
    (13.109, 21.495, 4.327, 0.948, -0.220),  # front tip
    (16.142, 17.698, 2.904, 1.046, 0.285),  # small, beside the front one
    (13.527, 13.664, 4.857, 0.974, 0.986),  # the middle one, crowning the heap
]
HOT_R = [6.581, 4.760, 3.430, 5.580, 5.001, 3.254, 5.888]
HOT_C = {0: (7.258, 8.966), 1: (18.024, 7.340), 3: (6.039, 18.092), 4: (13.278, 21.469), 5: (16.292, 17.698)}
# height factor (vertical half axis / plan radius), lift of the centre above the ground (px)
HEIGHT = [(0.84, 2.2), (0.88, 1.8), (0.92, 1.2), (0.84, 2.0), (0.88, 1.8), (0.92, 1.6), (0.88, 3.6)]

# no bevelled-edge lift in the bake: smooth balls have no machined edges
EDGE_LIFT = 0.0
COLD_FRAMES = [155]
HOT_FRAMES = [157, 159, 161, 163, 165]
BODY_FRAMES = {157: 119, 159: 120, 161: 121, 163: 122, 165: 124}


def X(c):
    return (c - GW / 2) * U


def Y(r):
    return (GH / 2 - r) * U


def balls(hot):
    out = []
    for i, (c, r, rad, e, ang) in enumerate(COLD):
        if hot:
            c, r = HOT_C.get(i, (c, r))
            rad = HOT_R[i]
        out.append((c, r, rad, e, ang, *HEIGHT[i]))
    return out


def materials(sprite, tag):
    # satin-glossy shell: a little metallic so the grazing reflection stays red, not a pale rim
    body = common.palette_material(sprite, 117, f"{NAME}_{tag}", metallic=0.65, roughness=0.34,
                                   frames=BODY_FRAMES)
    return [body]


def ball(bm, b, mat):
    """One ball: a near-sphere (plan ellipse r*e x r/e at `ang`, upper vertical half axis hf*r),
    its girth `lift` px above the ground; below the girth a flatter half (vertical half axis =
    lift) closes it on the ground at its bottom pole: a heavy ball resting on the ground, smooth all
    round, no cut edge."""
    c, r, rad, e, ang, hf, lift = b
    seg, rings = (24, 14) if rad > 3.6 else (18, 12)   # even: a ring on the girth
    cx, cy = X(c), Y(r)
    k = (1 + 1 / math.cos(math.pi / seg)) / 2   # the polygon's edges cut inside the fitted ellipse
    ax, ay = rad * e * U * k, rad / e * U * k
    rz = hf * rad * U
    zc = lift * U
    t = -ang   # image y is down, Blender Y up
    ct, st = math.cos(t), math.sin(t)
    top = bm.verts.new((cx, cy, zc + rz))
    bot = bm.verts.new((cx, cy, 0.0))
    rs = []
    for i in range(1, rings):
        phi = math.pi * i / rings
        sr = math.sin(phi)
        z = zc + (rz if phi <= math.pi / 2 else zc) * math.cos(phi)
        ring = []
        for j in range(seg):
            th = 2 * math.pi * j / seg
            u, v = ax * sr * math.cos(th), ay * sr * math.sin(th)
            ring.append(bm.verts.new((cx + u * ct - v * st, cy + u * st + v * ct, z)))
        rs.append(ring)
    fs = [bm.faces.new((top, rs[0][j], rs[0][(j + 1) % seg])) for j in range(seg)]
    for a, b_ in zip(rs, rs[1:]):
        fs += [bm.faces.new((a[j], b_[j], b_[(j + 1) % seg], a[(j + 1) % seg])) for j in range(seg)]
    fs += [bm.faces.new((bot, rs[-1][(j + 1) % seg], rs[-1][j])) for j in range(seg)]
    for f in fs:
        f.material_index = mat
        f.smooth = True


def build(coll, sprite, hot):
    tag = "hot" if hot else "cold"
    mats = materials(sprite, tag)
    bm = bmesh.new()
    for b in balls(hot):
        ball(bm, b, 0)
    me = bpy.data.meshes.new(f"{NAME}_{tag}")
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(f"{NAME}_{tag}", me)
    coll.objects.link(obj)
    for m in mats:
        me.materials.append(m)
    return obj, mats


def bake_maps(obj, out_dir, nmats, prefix, size=512, samples=64):
    """AO/roughness bake only (D50): usp_talon.bake_maps copied here (shared files are not ours to
    edit) with wider UV island margins (0.02), the images pre-filled with the neutral value
    instead of black, a 16 px extend margin, and images named <prefix>_*."""
    _bake(obj, out_dir, size, samples, (1.0, 0.97, 0.94), tuple(range(nmats)), prefix)


def _bake(obj, out_dir, size, samples, TINT, TEXTURED, prefix):
    """UV the model (Smart UV Project) and bake two maps with Cycles: a grey colour multiplier
    (ambient occlusion at two scales, so panel gaps and the nacelle roots darken, plus a light
    lift on bevelled edges) and a metallic-roughness map (G roughness, B metallic). Wire them into
    the palette materials: Base Color = map x palette colour, as texture_bake.py does."""
    scene = bpy.context.scene
    try:
        scene.render.engine = "CYCLES"
    except TypeError:
        pass
    scene.cycles.samples = samples
    scene.cycles.device = "CPU"
    try:  # Metal GPU when there is one
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for dev in prefs.devices:
            dev.use = True
        if any(d.type == "METAL" for d in prefs.devices):
            scene.cycles.device = "GPU"
    except Exception as err:
        print("newshe-155: no GPU bake", err)
    me = obj.data
    uv = me.uv_layers.new(name="bake")
    me.uv_layers.active = uv
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.02, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.02)
    bpy.ops.object.mode_set(mode="OBJECT")

    col_img = bpy.data.images.new(f"{prefix}_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new(f"{prefix}_rm", size // 2, size // 2, alpha=False)
    rm_img.colorspace_settings.name = "Non-Color"
    # neutral background, not black: colour 1.0 x tint, roughness/metal of the first material
    b0 = next(n for n in me.materials[0].node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    for img, c in ((col_img, (*TINT, 1.0)),
                   (rm_img, (1.0, b0.inputs["Roughness"].default_value, b0.inputs["Metallic"].default_value, 1.0))):
        img.pixels.foreach_set([v for _ in range(img.size[0] * img.size[1]) for v in c])

    mats = list(me.materials)
    saved = {}
    for i, m in enumerate(mats):
        nt = m.node_tree
        out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
        saved[m.name] = out.inputs["Surface"].links[0].from_socket if out.inputs["Surface"].links else None

    def bake_shader(m, mode):
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        rough = bsdf.inputs["Roughness"].default_value
        metal = bsdf.inputs["Metallic"].default_value
        N = nt.nodes.new
        L = nt.links.new
        tmp = []

        def node(kind):
            n = N(kind)
            tmp.append(n)
            return n

        def math_(op, a, b=None):
            n = node("ShaderNodeMath")
            n.operation = op
            n.use_clamp = op in ("MULTIPLY_ADD",)
            for k, v in enumerate((a, b)):
                if v is None:
                    continue
                if isinstance(v, (int, float)):
                    n.inputs[k].default_value = v
                else:
                    L(v, n.inputs[k])
            return n.outputs[0]
        ao_s = node("ShaderNodeAmbientOcclusion")
        ao_s.samples = 24
        ao_s.inputs["Distance"].default_value = 0.05   # deeper crevices: the sprite's dark gaps between balls
        ao_l = node("ShaderNodeAmbientOcclusion")
        ao_l.samples = 24
        ao_l.inputs["Distance"].default_value = 0.16
        bev = node("ShaderNodeBevel")
        bev.samples = 8
        bev.inputs["Radius"].default_value = 0.005
        geo = node("ShaderNodeNewGeometry")
        dot = node("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        L(bev.outputs["Normal"], dot.inputs[0])
        L(geo.outputs["True Normal"], dot.inputs[1])
        edge = math_("MINIMUM", math_("MULTIPLY", math_("SUBTRACT", 1.0, dot.outputs["Value"]), 8.0), 1.0)
        occl = math_("MULTIPLY", math_("POWER", ao_s.outputs["AO"], 1.6),
                     math_("ADD", 0.65, math_("MULTIPLY", ao_l.outputs["AO"], 0.35)))
        em = node("ShaderNodeEmission")
        if mode == "colour":
            v = math_("MINIMUM", math_("ADD", math_("ADD", 0.48, math_("MULTIPLY", occl, 0.62)),
                                       math_("MULTIPLY", edge, EDGE_LIFT)), 1.0)
            tint = node("ShaderNodeCombineColor")
            for k in range(3):
                L(math_("MULTIPLY", v, TINT[k]), tint.inputs[k])
            L(tint.outputs[0], em.inputs["Color"])
        else:
            r = math_("ADD", rough, math_("SUBTRACT", math_("MULTIPLY", math_("SUBTRACT", 1.0, occl), 0.3),
                                          math_("MULTIPLY", edge, EDGE_LIFT)))
            r = math_("MAXIMUM", math_("MINIMUM", r, 1.0), 0.05)
            comb = node("ShaderNodeCombineColor")
            comb.inputs[0].default_value = 1.0
            L(r, comb.inputs[1])
            comb.inputs[2].default_value = metal
            L(comb.outputs[0], em.inputs["Color"])
        out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
        L(em.outputs[0], out.inputs["Surface"])
        tgt = node("ShaderNodeTexImage")
        tgt.image = col_img if mode == "colour" else rm_img
        uvn = node("ShaderNodeUVMap")
        uvn.uv_map = "bake"
        L(uvn.outputs["UV"], tgt.inputs["Vector"])
        nt.nodes.active = tgt
        return tmp

    for mode, img in (("colour", col_img), ("rm", rm_img)):
        tmps = {m.name: bake_shader(m, mode) for m in mats}
        bpy.ops.object.bake(type="EMIT", margin=16, margin_type="EXTEND", use_clear=False)
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

    for i in TEXTURED:
        m = mats[i]
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


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sprite = common.load_sprite(WT, NAME)
    coll = common.reset_collection(NAME)
    # --factory-startup's default cube (+-1 m) stays in the scene: the model fills it nearly to its
    # walls, and the AO bake saw them (dark arcs on the front and left balls). Stray meshes go far
    # away and out of render (removing them leaves a dangling selection that outline_shell trips on).
    for o in list(bpy.data.objects):
        if o.type == "MESH" and coll not in o.users_collection:
            o.location.z -= 1000.0
            o.hide_render = True
    fmt = "AUTO"
    objs = []
    for hot in (False, True):
        obj, mats = build(coll, sprite, hot)
        tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
        print(f"{obj.name}: {len(obj.data.polygons)} faces, {tris} triangles")
        if "--no-bake" not in argv:
            bake_dir = HERE / "bake"
            bake_dir.mkdir(parents=True, exist_ok=True)
            hidden = [o for o in coll.objects if o is not obj]   # bake each body alone (no AO from the other)
            for o in hidden:
                o.hide_render = True
            bake_maps(obj, bake_dir, len(mats), f"eggs155_{'hot' if hot else 'cold'}")
            for o in hidden:
                o.hide_render = False
            fmt = "WEBP"
        shell = common.outline_shell(obj, coll, voxel=0.01, faces=1100, smooth=6)
        shell.name = shell.data.name = f"{obj.name}_outline"
        frames = HOT_FRAMES if hot else COLD_FRAMES
        common.frame_part(obj, frames)
        common.frame_part(shell, frames)
        objs += [obj, shell]
    common.export_sprite_model(ROOT, objs, MODEL, sprite["sprites"], image_format=fmt)


if __name__ == "__main__":
    main()
