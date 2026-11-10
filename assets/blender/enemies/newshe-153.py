"""newshe-153, design A: a cluster of fleshy brown bulbs (a fungus heap) on the ground.

Reading of the sprite (24x28, newshe.shp 153): seven round lumps, each lit from the upper right
(the 73-77 spots are sheen on a round surface, not paint or bumps), the darkest pixels are the
shadowed lower flanks and the ink ring. Material: organic (satin, slightly wet), so each lump is a
smooth swollen bulb: an ellipsoid whose widest girth stands a little above the ground (an undercut
belly that reads as a bulb, not a dome), with shallow vertical lobes, a flared fleshy foot where it
grows out of the ground and, between the bulbs, a low root mat and a few small buds that only the
side views see.

Footprints: a union of ellipses fitted to the sprite's inner mask (fit.py, D74), held near the
lumps the shading shows. Colour: each bulb's palette index is the median of its pixels without the
darkest (65-67) and brightest (73-77) steps: 69, the back-right bulb and the two small right ones 70.

Run: tools/build-models.sh -j 2 assets/blender/enemies/newshe-153.py   (or Blender -b -P this -- [--no-bake])
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
WT = HERE.parents[2]
sys.path.insert(0, str(HERE.parent))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

NAME = "newshe-153"
MODEL = f"enemies/{NAME}"
U = 1 / 12
GW, GH = 24, 28

# Bulbs: (centre col, centre row in px (pixel c spans c..c+1), half axes rx, ry px, angle deg of
# the rx axis in the image (y down), palette index, height factor, lift, lobes, lobe phase)
BULBS = [
    (7.48, 8.61, 6.65, 5.20, 25.3, 69, 0.80, 0.00, 7, 0.3),   # big, back left
    (17.90, 6.70, 3.51, 4.06, 70.1, 70, 0.92, 0.00, 6, 1.1),  # round, back right
    (20.11, 13.11, 2.87, 2.23, -2.6, 70, 0.90, 0.00, 5, 0.6),  # small, right
    (7.05, 17.91, 6.29, 4.87, -12.7, 69, 0.80, 0.00, 7, 2.0),  # big, front left
    (13.29, 21.44, 4.15, 4.41, 3.4, 69, 0.86, 0.00, 6, 0.9),  # front
    (16.40, 17.29, 3.25, 2.45, -125.8, 70, 0.92, 0.02, 5, 1.7),  # small, beside the front one
    (13.70, 12.70, 4.60, 4.20, 284.9, 69, 0.90, 0.05, 7, 0.2),  # the middle one, crowning the heap
    (17.27, 10.95, 4.01, 3.05, 28.5, 69, 0.90, 0.04, 6, 1.4),  # between the middle and back right
]
LOBE = 0.012
LEAN = 0.22
HEAP = (12.5, 14.5)      # lobe depth (fraction of radius)
SEG, RINGS = 30, 10


def X(c):
    return (c - GW / 2) * U


def Y(r):
    return (GH / 2 - r) * U


def materials(sprite):
    mats, slots = [], {}
    for b in BULBS:
        idx = b[5]
        if idx not in slots:
            slots[idx] = len(mats)
            mats.append(common.palette_material(sprite, idx, NAME, metallic=0.05, roughness=0.42))
    return mats, slots


def bulb(bm, b, mat):
    """One bulb: a lobed ellipsoid cut flat at z = 0 (a closed cap underneath), its widest girth
    at z = zc > 0, plus a flared foot ring hugging its base."""
    c, r, rx, ry, ang, _, hf, lift, nl, ph = b
    cx, cy = X(c), Y(r)
    ax, ay = rx * U, ry * U
    SEG = 22 if max(rx, ry) < 3.6 else 28
    RINGS = 8 if max(rx, ry) < 3.6 else 10
    rz = hf * min(ax, ay) * 1.05 + 0.08 * max(ax, ay)
    zc = 0.32 * rz + lift
    t = math.radians(-ang)  # world angle (image y is down)
    ct, st = math.cos(t), math.sin(t)
    # lean: the crown leans out from the heap's middle (bulbs pushed apart as they swell)
    ox, oy = cx - X(HEAP[0]), cy - Y(HEAP[1])
    ol = math.hypot(ox, oy) + 1e-9
    w = min(1.0, ol / (5 * U))
    lx, ly = LEAN * w * ox / ol, LEAN * w * oy / ol
    # polar angle where the ellipsoid meets the ground
    phig = math.acos(max(-0.98, -zc / rz))
    first = len(bm.faces)
    top = bm.verts.new((cx + lx * rz, cy + ly * rz, zc + rz))
    rings = []
    for i in range(1, RINGS + 1):
        phi = phig * (i / RINGS) ** 0.85
        s, cz = math.sin(phi), math.cos(phi)
        ring = []
        for j in range(SEG):
            th = 2 * math.pi * j / SEG
            # lobes fade out at the crown and at the foot
            w = math.sin(min(phi, math.pi / 2)) ** 2 * (1 - 0.6 * max(0.0, (phi - math.pi / 2) / (phig - math.pi / 2 + 1e-6)))
            k = 1 + LOBE * w * math.cos(nl * th + ph)
            u, v = ax * s * math.cos(th) * k, ay * s * math.sin(th) * k
            z = zc + rz * cz
            if i == RINGS:
                z = 0.0
            dz = max(0.0, z - zc)
            ring.append(bm.verts.new((cx + u * ct - v * st + lx * dz, cy + u * st + v * ct + ly * dz, z)))
        rings.append(ring)
    faces = []
    for j in range(SEG):
        faces.append(bm.faces.new((top, rings[0][j], rings[0][(j + 1) % SEG])))
    for a, bb in zip(rings, rings[1:]):
        for j in range(SEG):
            k = (j + 1) % SEG
            faces.append(bm.faces.new((a[j], bb[j], bb[k], a[k])))
    cap = bm.faces.new(list(reversed(rings[-1])))
    for f in faces:
        f.material_index = mat
        f.smooth = True
    cap.material_index = mat
    cap.smooth = False
    # flared foot: a fleshy collar where the bulb leaves the ground (inside the girth)
    base_s = math.sin(phig)
    fr = []
    prof = [(0.0, 1.0 + 0.10), (0.025, 1.0 + 0.05), (0.06, 1.0)]  # (z, radius factor vs ground ring)
    for z, f in prof:
        ring = []
        for j in range(SEG):
            th = 2 * math.pi * j / SEG
            k = 1 + 0.5 * LOBE * math.cos(nl * th + ph)
            gs = base_s * f * k
            # never wider than the girth
            gs = min(gs, 0.97)
            u, v = ax * gs * math.cos(th), ay * gs * math.sin(th)
            ring.append(bm.verts.new((cx + u * ct - v * st, cy + u * st + v * ct, z + (0 if z == 0 else 0))))
        fr.append(ring)
    for a, bb in zip(fr, fr[1:]):
        for j in range(SEG):
            k = (j + 1) % SEG
            f = bm.faces.new((a[j], a[k], bb[k], bb[j]))
            f.material_index = mat
            f.smooth = True
    capf = bm.faces.new(list(reversed(fr[0])))
    capf.material_index = mat
    topf = bm.faces.new(fr[-1])
    topf.material_index = mat
    return first, (cx, cy, ax, ay, t, rz, zc)


def bud(bm, x, y, r, h, mat, seg=14, rings=5):
    """A small round bud sitting on the ground."""
    zc = 0.3 * h
    top = bm.verts.new((x, y, zc + h))
    phig = math.acos(-zc / h)
    rs = []
    for i in range(1, rings + 1):
        phi = phig * i / rings
        z = 0.0 if i == rings else zc + h * math.cos(phi)
        rs.append([bm.verts.new((x + r * math.sin(phi) * math.cos(2 * math.pi * j / seg),
                                 y + r * math.sin(phi) * math.sin(2 * math.pi * j / seg), z)) for j in range(seg)])
    fs = [bm.faces.new((top, rs[0][j], rs[0][(j + 1) % seg])) for j in range(seg)]
    for a, b in zip(rs, rs[1:]):
        fs += [bm.faces.new((a[j], b[j], b[(j + 1) % seg], a[(j + 1) % seg])) for j in range(seg)]
    fs.append(bm.faces.new(list(reversed(rs[-1]))))
    for f in fs:
        f.material_index = mat
        f.smooth = True


def root_mat(bm, info, mat, inset=0.7):
    """A low fleshy mat under the heap, so no ground shows between the bulbs from the side views.
    Its outline is the union of the bulbs' ground footprints shrunk by `inset` px, traced as a
    star from the heap's centre (first exit along each ray), so it never pokes out past a bulb
    foot, not even in the notches where two bulbs pinch in."""
    import numpy as np
    feet = []
    for cx, cy, ax, ay, t, rz, zc in info:
        gs = min(math.sin(math.acos(max(-0.98, -zc / rz))) * 1.10, 0.97)
        feet.append((cx, cy, ax * gs - inset * U, ay * gs - inset * U, t))

    def inside(x, y):
        for cx, cy, a, b, t in feet:
            dx, dy = x - cx, y - cy
            u = dx * math.cos(t) + dy * math.sin(t)
            v = -dx * math.sin(t) + dy * math.cos(t)
            if (u / a) ** 2 + (v / b) ** 2 <= 1.0:
                return True
        return False
    c0, r0 = X(HEAP[0]), Y(HEAP[1])
    n, step = 64, 0.05 * U
    rad = np.zeros(n)
    for k in range(n):
        a = 2 * math.pi * k / n
        d = 0.0
        while inside(c0 + (d + step) * math.cos(a), r0 + (d + step) * math.sin(a)):
            d += step
        rad[k] = d
    rad = np.minimum(rad, 0.5 * (np.roll(rad, 1) + np.roll(rad, -1)) + 0.2 * U)  # no lone spikes
    lo, hi = [], []
    for k in range(n):
        a = 2 * math.pi * k / n
        lo.append(bm.verts.new((c0 + rad[k] * math.cos(a), r0 + rad[k] * math.sin(a), 0.0)))
        hi.append(bm.verts.new((c0 + 0.85 * rad[k] * math.cos(a), r0 + 0.85 * rad[k] * math.sin(a), 0.05)))
    fs = [bm.faces.new((lo[k], lo[(k + 1) % n], hi[(k + 1) % n], hi[k])) for k in range(n)]
    fs.append(bm.faces.new(hi))
    fs.append(bm.faces.new(list(reversed(lo))))
    for f in fs:
        f.material_index = mat
        f.smooth = True


def build(coll, sprite):
    mats, slots = materials(sprite)
    bm = bmesh.new()
    info = []
    for b in BULBS:
        _, inf = bulb(bm, b, slots[b[5]])
        info.append(inf)
    root_mat(bm, info, slots[69])
    # buds in the crevices at the ground (seen from the sides only; inside the top silhouette)
    for c, r, rp, hp in [(12.6, 7.7, 1.2, 1.5), (4.6, 13.4, 1.1, 1.3), (17.2, 14.8, 1.0, 1.2),
                         (9.9, 21.6, 1.0, 1.2)]:
        bud(bm, X(c), Y(r), rp * U, hp * U, slots[69])
    me = bpy.data.meshes.new(NAME)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(NAME, me)
    coll.objects.link(obj)
    for m in mats:
        me.materials.append(m)
    return obj, mats


def bake_maps(obj, out_dir, nmats, size=512, samples=64):
    """AO/roughness bake only (D50): usp_talon.bake_maps copied here (shared files are not ours to
    edit) with wider UV island margins (0.02), the images pre-filled with the neutral value
    instead of black, a 16 px extend margin, and images named bulbs153_*."""
    _bake(obj, out_dir, size, samples, (1.0, 0.97, 0.94), tuple(range(nmats)))


def _bake(obj, out_dir, size, samples, TINT, TEXTURED):
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
        print("newshe-153: no GPU bake", err)
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

    col_img = bpy.data.images.new("bulbs153_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new("bulbs153_rm", size // 2, size // 2, alpha=False)
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
        ao_s.inputs["Distance"].default_value = 0.03
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
        occl = math_("MULTIPLY", math_("POWER", ao_s.outputs["AO"], 0.8),
                     math_("ADD", 0.65, math_("MULTIPLY", ao_l.outputs["AO"], 0.35)))
        em = node("ShaderNodeEmission")
        if mode == "colour":
            v = math_("MINIMUM", math_("ADD", math_("ADD", 0.48, math_("MULTIPLY", occl, 0.62)),
                                       math_("MULTIPLY", edge, 0.2)), 1.0)
            tint = node("ShaderNodeCombineColor")
            for k in range(3):
                L(math_("MULTIPLY", v, TINT[k]), tint.inputs[k])
            L(tint.outputs[0], em.inputs["Color"])
        else:
            r = math_("ADD", rough, math_("SUBTRACT", math_("MULTIPLY", math_("SUBTRACT", 1.0, occl), 0.3),
                                          math_("MULTIPLY", edge, 0.16)))
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
    obj, mats = build(coll, sprite)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{NAME}: {len(obj.data.polygons)} faces, {tris} triangles")
    fmt = "AUTO"
    if "--no-bake" not in argv:
        import tempfile
        bake_dir = Path(tempfile.mkdtemp(prefix="bulbs153_"))
        bake_maps(obj, bake_dir, len(mats))
        fmt = "WEBP"
    shell = common.outline_shell(obj, coll, voxel=0.01, faces=1600, smooth=6)
    shell.name = shell.data.name = f"{NAME}_outline"
    common.export_sprite_model(WT, [obj, shell], MODEL, sprite["sprites"], image_format=fmt)


if __name__ == "__main__":
    main()
