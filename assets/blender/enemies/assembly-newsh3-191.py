"""assembly-newsh3-191, a stepped sandstone temple-pyramid (ziggurat) standing in the desert
(newsh3.shp 153 | 155 over 191 | 193, one 48x56 px tile; SURFACE 4.2).

What it is (read from the sprite, light from the upper left, drawn in the game's oblique view):
- Four terraces of dressed sandstone, each a battered block: a 1 px wall with a lit chamfered lip on
  the west, north and east, and on the south a broad talud (sloped face in shade, rows 37-42 on the
  base, 2 px on the upper terraces) under a lip and a deep south terrace. The terraces step back to
  the west, east and south; on the north each one stands a little further out than the one below
  (rows 11, 9, 7, 5 at the west end), so the back of the pyramid is a stepped sheer wall rising to
  the top terrace.
- On the top terrace a low platform (cols 16-28, rows 3-16) carries the pointed cap. The cap is its
  own enemy, newsh3-3 (drawn after the pyramid at the same place, dx +16, dy +2 from 153's corner), so
  the pyramid ends in a flat platform for it to stand on: D181's cover rule raises newsh3-3 to the top
  of 153/155, i.e. onto this platform. A cap built here as well would lift newsh3-3 into the air.
- Dark marks are depth: a doorway at the foot of the base talud (cols 25-26, rows 38-42), a vent grille
  (cols 35-39, rows 41-42) with a slot above it (col 38), and small window slots on the upper taluds
  (row 32 cols 28-29, row 26 cols 16-17, row 19 col 30).
- Lit lines are chamfered edges catching the light; the white pixel at the SW lip (row 36 col 3) is
  sheen. The sand and the pyramid's shadow on it are ground (D130): nothing is built for them; IoU is
  measured with ramp 160-175 transparent (refmask.py).

Run: blender -b --python assets/blender/enemies/assembly-newsh3-191.py [-- --nobake]
Writes public/models/enemies/newsh3-{153,155,191,193}.glb and their src/render/spriteModels entries
(each piece with its outline shell, AO/roughness baked from the model, D50). A build writes nothing else.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

WT = common.repo_root(__file__)

NAME = "assembly-newsh3-191"
PIECES = ["newsh3-153", "newsh3-155", "newsh3-191", "newsh3-193"]
# Piece centres relative to the tile centre (screen 92, 25): 153 (80, 11), 155 (104, 11), 191 (80, 39), 193 (104, 39).
LAYOUT = [("newsh3-153", -12, -14), ("newsh3-155", 12, -14), ("newsh3-191", -12, 14), ("newsh3-193", 12, 14)]
PX = 1 / 12


def X(u):
    return (u - 24) * PX


def Y(v):
    return (28 - v) * PX


def P(u, v, z):
    return Vector((X(u), Y(v), z))


# Terraces, bottom up: footprint pixel edges at the foot (west, east, north, south), top height, south
# talud depth in px (top view), batter of the west/east/north walls in px.
TIERS = [
    dict(w=2, e=41, n=11, s=43, z=0.40, f=6.0),
    dict(w=5, e=38, n=9, s=33, z=0.54, f=2.0),
    dict(w=8, e=35, n=7, s=27, z=0.68, f=2.0),
    dict(w=12, e=32, n=5, s=21, z=0.82, f=2.0),
]
PLAT = dict(w=16, e=28, n=3.4, s=16.2, z=0.855, f=0.6)  # the cap's platform (newsh3-3 stands on it)
BATTER = 0.62     # px the west/east/north walls lean in over a terrace's visible height
LIP = 0.85        # chamfer across (px) at each terrace's top edge: the sprite's 1 px lit line
LIPZ = 0.05       # and down (units)
CORNER = 0.45     # chamfer of the vertical corners (px)
COURSE = 0.0875   # masonry course height (units): a groove every course
GROOVE = 0.10     # groove depth (px)


def materials(sprite):
    tag = "n3_191a"

    def pal(i, roughness, spec=0.35):
        m = common.palette_material(sprite, i, tag + f"_{i}_{int(roughness * 100)}", metallic=0.0, roughness=roughness)
        bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        if "Specular IOR Level" in bsdf.inputs:
            bsdf.inputs["Specular IOR Level"].default_value = spec
        return m

    spec = [
        ("wwall", 21, 0.82), ("wlip", 27, 0.72), ("wtread", 24, 0.8),
        ("nwall", 21, 0.85), ("nlip", 25, 0.75), ("ntread", 24, 0.8),
        ("ewall", 19, 0.85), ("elip", 23, 0.78), ("etread", 22, 0.82),
        ("sface", 18, 0.88), ("slip", 21, 0.8), ("stread", 20, 0.85),
        ("e1wall", 18, 0.88),
        ("dark", 17, 0.95), ("frame", 19, 0.85), ("lintel", 20, 0.82),
        ("plat", 21, 0.85), ("platwall", 19, 0.88),
    ]
    mats, M, seen = [], {}, {}
    for key, idx, rough in spec:
        sig = (idx, rough)
        if sig not in seen:
            seen[sig] = len(mats)
            mats.append(pal(idx, rough))
        M[key] = seen[sig]
    return mats, M


def ring_pts(w, e, n, s, z, c=CORNER):
    """A chamfered rectangle (pixel edges) at height z, 8 points counter-clockwise seen from above,
    starting at the north edge's east end: N, NW, W, SW, S, SE, E, NE segments follow."""
    return [P(e - c, n, z), P(w + c, n, z), P(w, n + c, z), P(w, s - c, z),
            P(w + c, s, z), P(e - c, s, z), P(e, s - c, z), P(e, n + c, z)]


SEG = ["n", "nw", "w", "sw", "s", "se", "e", "ne"]


def edges_at(t, zb, z, inset=0.0):
    """Footprint edges (w, e, n, s) of terrace t at height z (zb = the top of the terrace below: the
    west, east and south faces start there; the north wall starts at the ground)."""
    h = max(t["z"] - zb, 1e-6)
    a = min(max((z - zb) / h, 0.0), 1.0)
    an = min(max(z / t["z"], 0.0), 1.0)
    return (t["w"] + BATTER * a + inset, t["e"] - BATTER * a - inset,
            t["n"] + BATTER * an + inset, t["s"] - t["f"] * a - inset)


def loft(bm, rings, mats_per_band, cap_bottom=True):
    vs = [[bm.verts.new(p) for p in r] for r in rings]
    for k, (a, b) in enumerate(zip(vs, vs[1:])):
        for i in range(8):
            f = bm.faces.new((a[i], a[(i + 1) % 8], b[(i + 1) % 8], b[i]))
            f.material_index = mats_per_band[k][i]
    if cap_bottom:
        f = bm.faces.new(list(reversed(vs[0])))
        f.material_index = mats_per_band[0][0]
    return vs


def terrace(bm, M, t, zb, nxt, detail=True, top_face=False):
    """One terrace: a battered, chamfered block from the ground to t['z'] with masonry grooves, a lip
    chamfer and the tread ring round the next terrace's foot (nxt: its edges at this height)."""
    wall = {"n": M["nwall"], "ne": M["ewall"], "e": M["ewall"] if zb > 0 else M["e1wall"],
            "se": M["sface"], "s": M["sface"], "sw": M["sface"], "w": M["wwall"], "nw": M["nwall"]}
    lip = {"n": M["nlip"], "ne": M["nlip"], "e": M["elip"], "se": M["slip"], "s": M["slip"], "sw": M["wlip"],
           "w": M["wlip"], "nw": M["wlip"]}
    tread = {"n": M["ntread"], "ne": M["etread"], "e": M["etread"], "se": M["stread"], "s": M["stread"],
             "sw": M["wtread"], "w": M["wtread"], "nw": M["wtread"]}
    z1 = t["z"]
    zs = [0.0]
    if zb > 0:
        zs.append(zb)
    rings, bands = [], []
    # Masonry: a V groove at every course line under the lip.
    grooves = []
    if detail:
        k = 1
        while k * COURSE < z1 - LIPZ - 0.03:
            grooves.append(k * COURSE)
            k += 1
    pts = sorted(set(zs + [z1 - LIPZ]))
    seq = []
    for z in pts:
        seq.append((z, 0.0))
    for g in grooves:
        seq += [(g - 0.007, 0.0), (g, GROOVE), (g + 0.007, 0.0)]
    seq.sort()
    for z, ins in seq:
        rings.append(ring_pts(*edges_at(t, zb, z, inset=ins), z))
    wb = [wall[s] for s in SEG]
    bands = [wb] * (len(rings) - 1)
    # The lip: a chamfer up to the top face, inset LIP.
    w, e, n, s = edges_at(t, zb, z1)
    rings.append(ring_pts(w + LIP, e - LIP, n + LIP, s - LIP, z1, c=CORNER * 0.8))
    bands.append([lip[s_] for s_ in SEG])
    vs = loft(bm, rings, bands)
    top = vs[-1]
    if top_face:
        f = bm.faces.new(top)
        f.material_index = M["plat"]
        return
    # Tread ring: from the lip's inner edge to the next terrace's foot (clamped north to the lip).
    tw, te, tn, ts = w + LIP, e - LIP, n + LIP, s - LIP
    nw_, ne_, nn_, ns_ = nxt
    iw, ie, inn, isb = max(tw + 0.05, nw_), min(te - 0.05, ne_), max(tn, nn_), min(ts - 0.05, ns_)
    inner = [bm.verts.new(p) for p in ring_pts(iw, ie, inn, isb, z1, c=CORNER * 0.8)]
    for i in range(8):
        a, b = top[i], top[(i + 1) % 8]
        c_, d = inner[(i + 1) % 8], inner[i]
        if (a.co - d.co).length < 1e-6 and (b.co - c_.co).length < 1e-6:
            continue
        if SEG[i] == "n" and inn - tn < 1e-6:
            continue
        try:
            f = bm.faces.new((a, b, c_, d))
        except ValueError:
            continue
        f.material_index = tread[SEG[i]]


def on_talud(t, zb, u, v, out=0.0):
    """A point on terrace t's south talud at column u, row v, pushed `out` units along its normal."""
    h = t["z"] - zb
    a = min(max((t["s"] - v) / t["f"], 0.0), 1.0)
    z = zb + a * h
    run = t["f"] * PX
    nrm = Vector((0, -h, run)).normalized()
    return P(u, v, z) + nrm * out


def talud_slab(bm, t, zb, u0, u1, v0, v1, z_out0, z_out1, mat):
    """A slab on the talud between columns u0..u1 and rows v0..v1, from z_out0 to z_out1 along the
    face normal (negative = sunk into the face)."""
    pts = []
    for u in (u0, u1):
        for v in (v0, v1):
            for o in (z_out0, z_out1):
                pts.append(on_talud(t, zb, u, v, o))
    a_hull(bm, pts, mat)


def a_hull(bm, pts, mat):
    tmp = bmesh.new()
    for p in pts:
        tmp.verts.new(p)
    res = bmesh.ops.convex_hull(tmp, input=tmp.verts[:])
    junk = res["geom_interior"] + res["geom_unused"]
    if junk:
        bmesh.ops.delete(tmp, geom=list({g for g in junk if isinstance(g, bmesh.types.BMVert)}), context="VERTS")
    bmesh.ops.dissolve_limit(tmp, angle_limit=math.radians(0.5), verts=tmp.verts[:], edges=tmp.edges[:])
    for f in tmp.faces:
        f.material_index = mat
    me = bpy.data.meshes.new("tmp")
    tmp.to_mesh(me)
    tmp.free()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)


def details(bm, M):
    t1, t2, t3, t4 = TIERS
    # Doorway at the foot of the base talud: a dark opening in a stepped frame with a lintel.
    talud_slab(bm, t1, 0.0, 24.7, 26.7, 38.0, 43.0, -0.01, 0.006, M["dark"])
    talud_slab(bm, t1, 0.0, 24.0, 24.7, 37.6, 43.0, -0.01, 0.026, M["frame"])
    talud_slab(bm, t1, 0.0, 26.7, 27.4, 37.6, 43.0, -0.01, 0.026, M["frame"])
    talud_slab(bm, t1, 0.0, 23.7, 27.7, 37.0, 37.7, -0.01, 0.034, M["lintel"])
    # Vent grille at the base's south-east foot (rows 41-42) and the slot above it (col 38).
    talud_slab(bm, t1, 0.0, 34.9, 39.3, 40.9, 43.0, -0.01, 0.005, M["dark"])
    for u in (35.9, 37.0, 38.1):
        talud_slab(bm, t1, 0.0, u, u + 0.42, 40.9, 43.0, -0.01, 0.02, M["frame"])
    talud_slab(bm, t1, 0.0, 34.6, 39.6, 40.5, 40.95, -0.01, 0.024, M["lintel"])
    talud_slab(bm, t1, 0.0, 37.7, 38.7, 37.5, 40.3, -0.01, 0.005, M["dark"])
    # Window slots on the upper taluds.
    talud_slab(bm, t2, t1["z"], 27.9, 29.9, 31.4, 32.8, -0.01, 0.005, M["dark"])
    talud_slab(bm, t3, t2["z"], 15.9, 17.9, 25.4, 26.8, -0.01, 0.005, M["dark"])
    talud_slab(bm, t4, t3["z"], 29.5, 30.7, 19.2, 20.6, -0.01, 0.005, M["dark"])


def build(coll, detail=True, name=NAME):
    sprite = common.load_sprite(WT, PIECES[0])
    for n in PIECES[1:]:
        sprite["colors"].update(common.load_sprite(WT, n)["colors"])
    mats, M = materials(sprite)
    bm = bmesh.new()
    zb = 0.0
    seq = TIERS + [PLAT]
    for i, t in enumerate(seq):
        if i + 1 < len(seq):
            nxt = edges_at(seq[i + 1], t["z"], t["z"])
            terrace(bm, M, t, zb, nxt, detail)
        else:
            terrace(bm, M, t, zb, None, detail, top_face=True)
        zb = t["z"]
    if detail:
        details(bm, M)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)
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


def split_open(obj, layout):
    """common.split_assembly without filling the cuts (for the outline shell)."""
    result = {}
    coll = obj.users_collection[0]
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)
        hw, hh = 12 / 12, 14 / 12
        for co, no in (((x0 - hw, 0, 0), (-1, 0, 0)), ((x0 + hw, 0, 0), (1, 0, 0)),
                       ((0, y0 - hh, 0), (0, -1, 0)), ((0, y0 + hh, 0), (0, 1, 0))):
            geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
            bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        mesh = bpy.data.meshes.new(name + "_outline")
        bm.to_mesh(mesh)
        bm.free()
        for mat in obj.data.materials:
            mesh.materials.append(mat)
        piece = bpy.data.objects.new(name + "_outline", mesh)
        coll.objects.link(piece)
        result[name] = piece
    return result



# --- helpers copied from the design folder (no shared file edited) ---


def bake_maps(obj, tag, size=1024, samples=48):
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
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.003, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.002)
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
        ao_s.inputs["Distance"].default_value = 0.03
        ao_l = node("ShaderNodeAmbientOcclusion")
        ao_l.samples = 24
        ao_l.inputs["Distance"].default_value = 0.14
        bev = node("ShaderNodeBevel")
        bev.samples = 8
        bev.inputs["Radius"].default_value = 0.004
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
    """Keep the outline shell under the model's top surface (D90/D118: ink on the silhouette only).

    The voxel shell is smoothed, so it bridges the model's creases (the hood's trim strips, the gem bezel, the
    engine-bay channel, the hood/nose step) and stood above the surface there: its back faces drew as dark
    scribbles across the hood and the plate. Every shell vertex is dropped to `margin` under the topmost
    model surface within `reach` of it (seen from straight above). x and y are untouched, so the silhouette (and the ink round it) is
    the same."""
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get()
    tree = BVHTree.FromObject(model, dg)
    mw = shell.matrix_world
    inv = mw.inverted()
    moved = 0
    for v in shell.data.vertices:
        w = mw @ v.co
        hit = tree.ray_cast(Vector((w.x, w.y, 5.0)), Vector((0, 0, -1)))
        if hit[0] is None:
            continue
        zt = hit[0].z
        for k in range(12):  # the lowest top within `reach`: a shell edge spans ~0.6 px, so a vertex
            a = 2 * math.pi * k / 12  # beside a raised strip must not ride at the strip's height
            for rad in (0.35 * reach, 0.7 * reach, reach):
                h = tree.ray_cast(Vector((w.x + rad * math.cos(a), w.y + rad * math.sin(a), 5.0)), Vector((0, 0, -1)))
                if h[0] is not None:
                    zt = min(zt, h[0].z)
        zt -= margin
        if w.z > zt:
            v.co = inv @ Vector((w.x, w.y, zt))
            moved += 1
    shell.data.update()
    print(shell.name, "sunk", moved, "of", len(shell.data.vertices))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    coll = common.reset_collection(NAME)
    obj = build(coll)
    pieces = common.split_assembly(obj, LAYOUT)
    # The outline shell (D51/D90): one shell from a sealed copy of the whole pyramid without grooves or
    # door/vent detail, kept under the top surfaces (sink_shell), then cut into the pieces WITHOUT
    # filling the cuts, so no shell wall stands at the seams between pieces (it drew ink lines there).
    plain = build(coll, detail=False, name=NAME + "_plain")
    bpy.context.view_layer.update()
    whole = common.outline_shell(plain, coll, voxel=0.018, faces=14000, inside=0.02, islands="outer")
    sink_shell(whole, plain, margin=0.08, reach=0.22)
    whole_props = {k: whole[k] for k in whole.keys() if k.startswith("tyrian")}
    shell_mat = list(whole.data.materials)
    shells = split_open(whole, LAYOUT)
    bpy.data.objects.remove(whole, do_unlink=True)
    bpy.data.objects.remove(plain, do_unlink=True)
    for name, cx, cy in LAYOUT:
        p = pieces[name]
        for poly in p.data.polygons:
            poly.use_smooth = True
        p.data.set_sharp_from_angle(angle=math.radians(30))
        sh = shells[name]
        sh.name = sh.data.name = f"{name}_outline"
        for poly in sh.data.polygons:
            poly.use_smooth = True
        for k, v in whole_props.items():
            sh[k] = v
        print("SHELL", name, len(sh.data.vertices), "verts")
        assert len(sh.data.vertices) > 0, name
    bake = "--nobake" not in argv
    if bake:
        obj.hide_render = True
        for name, cx, cy in LAYOUT:
            shells[name].hide_render = True
            pieces[name].location = (cx / 12, -cy / 12, 0)
        bpy.context.view_layer.update()
        for name, _, _ in LAYOUT:
            p = pieces[name]
            tag = name.replace("-", "_") + "_a"
            for i, m in enumerate(list(p.data.materials)):
                c = m.copy()
                c.name = m.name.replace("_n3_191a", f"_{tag}")
                p.data.materials[i] = c
            bake_maps(p, tag)
        for name, _, _ in LAYOUT:
            pieces[name].location = (0, 0, 0)
            shells[name].hide_render = False
        obj.hide_render = False
        bpy.context.view_layer.update()
    fmt = "WEBP" if bake else "AUTO"
    for name, _, _ in LAYOUT:
        common.export_sprite_model(WT, [pieces[name], shells[name]], f"enemies/{name}",
                                   common.load_sprite(WT, name)["sprites"], image_format=fmt)


if __name__ == "__main__":
    main()
