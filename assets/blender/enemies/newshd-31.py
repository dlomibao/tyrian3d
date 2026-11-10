"""Rock-heap corner fillers (newshd.shp 31 and 15, 12x14 tiles), design A: a 3D version of their sprites.

Seen in level 1.1 (ASTEROID1). IDENTITY: edge pieces of the drifting rock heap assembly-newshd-89
(D121): enemy types 444 (31) and 446 (15) sit in that heap's type block and spawn with it. Each fills
one concave corner of the heap's outline: 31 the lower-right quarter of the heap's missing top-left
piece (it abuts newshd-13 on its right and newshd-49 below), 15 the lower-left quarter of the missing
top-right piece (it abuts newshd-13 on its left and newshd-53 below). So each is one or a few more of
the heap's boulders, built the way assembly-newshd-89 builds its boulders (D116/D121, D65):

  1. The sprite's inner mask (tools/sprite_mask.py, D74) is cut into cells (CELLS: a seed per boulder,
     pixels to the nearest seed). Each cell's foot polygon runs through the pixel-edge midpoints.
  2. Each boulder: the foot at z 0, sections stepped in towards its crown along a pchip profile
     (dome / flat kinds as the heap), jittered; the convex hull gives planar fracture faces; coplanar
     triangles merge; every edge gets a small chamfer.
  3. Underneath, the heap floats in an asteroid field (D122 audit): the hull also takes a rounded belly
     (two inset rings and a keel point below z 0), so the underside is closed rock, not a flat base.
  4. Each boulder is intersected with the outline clip (the inner mask, vertical for 0.5 px, then
     leaning in along the heap's CLIP_PROFILE, also along the tile edges where the heap carries on, so
     these boulders meet the heap's leaning flanks in the same V cracks its own boulders meet in).
  5. Palette: each boulder takes the median of its cell's pixels between the 15th and 85th luminance
     percentile (ink, deepest shading and glints are lighting). Rock: metallic 0, roughness 0.85.
     AO/edge colour multiplier + roughness bake, no concept projection.
  6. Outline shell (D51) of each model.
Underside: the rounded belly, closed. Nothing more.

Run: blender -b --factory-startup --python assets/blender/enemies/newshd-31.py -- [--no-bake] [--render DIR] [--context DIR]
Exports public/models/enemies/newshd-31.glb and newshd-15.glb (merged item) and their spriteModels json.
"""

import math
import random
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))
sys.path.insert(0, str(WT / "tools"))
import common  # noqa: E402
import sprite_mask as SM  # noqa: E402
import usp_talon as T  # noqa: E402

OUT = Path(__file__).resolve().parent
PX = 1 / 12
W, H = 12, 14
CHAMFER = 0.28
TAPER_PX = 1.2
CLIP_PROFILE = [(-12.0, 0.0), (0.5, 0.05), (3.0, 1.0), (8.0, 2.8), (16.0, 5.0)]  # assembly-newshd-89's
CLIP_TOL = 0.45
FOOT_TOL = 0.45
AWAY = Vector((0.8, -0.6)).normalized()  # light from the upper left: flat faces fall to the lower right

# Boulders per model: seed pixel (col, row), height px, kind, crest (col,row pairs) optional.
MODELS = {
    "newshd-31": {
        "seed": 31,
        "clip": [(-12.0, 0.0), (0.5, 0.05), (3.0, 1.0), (7.0, 2.4)],
        "taper": TAPER_PX,
        "grow": 0.0,
        "cells": [
            # the lit lump (sprite 9/10 at column 9, rows 9-10): the highest crown, near the heap corner
            {"name": "lump", "seed": (9.3, 9.6), "h": 5.8, "kind": "dome", "peak": (9.2, 9.6)},
            # the lit ledge along the bottom (the 8s, rows 12-13): a long ridge that runs into the heap
            {"name": "ledge", "seed": (4.8, 12.3), "h": 4.6, "kind": "dome", "peak": (5.6, 12.6),
             "crest": ((2.5, 12.9), (7.2, 12.4))},
            # the darker upper wedge (4/5/6, rows 3-8): a fracture face falling away from the light
            {"name": "upper", "seed": (10.4, 5.6), "h": 3.4, "kind": "flat", "peak": (10.4, 7.0)},
        ],
    },
    "newshd-15": {
        "seed": 15,
        "clip": [(-12.0, 0.0), (0.8, 0.0), (4.0, 0.45)],
        "taper": 0.35,
        "grow": 0.0,
        # the 1-px tip at row 9 lost half its pixel to the midpoint line: the outline runs to its corner
        "extra": [(0.92, 9.08)],
        "cells": [
            {"name": "sliver", "seed": (0.8, 11.8), "h": 2.5, "kind": "dome", "peak": (0.6, 12.4)},
        ],
    },
}


# --- sprite ---------------------------------------------------------------------------------------

def luma(rgb):
    return 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]


def label_cells(inner, cells):
    lab = [[-1] * W for _ in range(H)]
    for y in range(H):
        for x in range(W):
            if inner[y][x]:
                lab[y][x] = min(range(len(cells)), key=lambda i: (cells[i]["seed"][0] - (x + 0.5)) ** 2
                                + (cells[i]["seed"][1] - (y + 0.5)) ** 2)
    return lab


def cell_colour(idx, colors, lab, i):
    vals = sorted((luma(colors[idx[y][x]]), idx[y][x]) for y in range(H) for x in range(W)
                  if lab[y][x] == i and idx[y][x] in colors and luma(colors[idx[y][x]]) >= SM.INK_LUMA)
    print("A: cell", i, [v for _, v in vals])
    lo, hi = int(len(vals) * 0.15), max(int(len(vals) * 0.85), int(len(vals) * 0.15) + 1)
    band = vals[lo:hi]
    return band[len(band) // 2][1]


def trace(mask):
    edges = {}
    for y in range(H):
        for x in range(W):
            if not mask[y][x]:
                continue

            def on(yy, xx):
                return 0 <= yy < H and 0 <= xx < W and mask[yy][xx]
            if not on(y - 1, x):
                edges[(x + 1, y)] = (x, y)
            if not on(y, x - 1):
                edges[(x, y)] = (x, y + 1)
            if not on(y + 1, x):
                edges[(x, y + 1)] = (x + 1, y + 1)
            if not on(y, x + 1):
                edges[(x + 1, y + 1)] = (x + 1, y)
    best, seen = [], set()
    for s in list(edges):
        if s in seen:
            continue
        loop, p = [], s
        while p not in seen and p in edges:
            seen.add(p)
            loop.append(p)
            p = edges[p]
        if len(loop) > len(best):
            best = loop
    return best


def outline_poly(loop):
    """Corner loop -> polygon (px frame, X right, Y up). Along the tile's own edges (where the heap
    carries on) the polygon keeps the pixel corners, elsewhere it runs through the edge midpoints."""
    out = []
    n = len(loop)
    for i in range(n):
        (x1, y1), (x2, y2) = loop[i], loop[(i + 1) % n]
        on_edge = (x1 == x2 and x1 in (0, W)) or (y1 == y2 and y1 in (0, H))
        if on_edge:
            out.append((x1 - W / 2, H / 2 - y1))
        out.append(((x1 + x2) / 2 - W / 2, H / 2 - (y1 + y2) / 2))
    # drop duplicates
    res = []
    for p in out:
        if not res or (abs(res[-1][0] - p[0]) > 1e-6 or abs(res[-1][1] - p[1]) > 1e-6):
            res.append(p)
    return res


def simplify(pts, tol):
    def dp(seq):
        if len(seq) < 3:
            return seq
        a, b = Vector(seq[0]), Vector(seq[-1])
        ab = b - a
        L = ab.length or 1e-9
        best, bi = 0, 0
        for i in range(1, len(seq) - 1):
            p = Vector(seq[i])
            d = abs(ab.x * (a.y - p.y) - ab.y * (a.x - p.x)) / L
            if d > best:
                best, bi = d, i
        if best <= tol:
            return [seq[0], seq[-1]]
        return dp(seq[:bi + 1])[:-1] + dp(seq[bi:])
    k = max(range(len(pts)), key=lambda i: pts[i][0] + 0.37 * pts[i][1])
    seq = pts[k:] + pts[:k]
    a = Vector(seq[0])
    j = max(range(len(seq)), key=lambda i: (Vector(seq[i]) - a).length)
    return dp(seq[:j + 1])[:-1] + dp(seq[j:] + [seq[0]])[:-1]


def cr(col, row):
    """sprite (col, row) -> px frame (X right, Y up, tile centre 0)."""
    return Vector((col - W / 2, H / 2 - row))


# --- geometry --------------------------------------------------------------------------------------

def nearest_on_seg(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-9)))
    return a + ab * t


def boulder_points(foot, cell, rng, taper=TAPER_PX):
    h = cell["h"]
    kind = cell["kind"]
    peak = cr(*cell["peak"])
    crest = [cr(*c) for c in cell["crest"]] if cell.get("crest") else None
    pts = [(x, y, 0.0) for x, y in foot]
    if kind == "flat":
        prof = [(0.0, 0.0), (0.12, 0.42), (0.3, 0.78), (0.5, 0.95)]
        stations = [0.1, 0.24, 0.38, 0.5]
    else:
        prof = [(0.0, 0.0), (0.24, 0.36), (0.46, 0.72), (0.66, 0.92), (0.8, 0.99)]
        stations = [0.14, 0.34, 0.56, 0.74]
    zf = T.pchip([s for s, _ in prof], [z for _, z in prof])
    for k, s in enumerate(stations):
        step = 1 if k == 0 else 2 + k // 2
        for j in range(0, len(foot), step):
            p = Vector(foot[j])
            c = nearest_on_seg(p, crest[0], crest[1]) if crest else peak
            q = p + (c - p) * (s + rng.uniform(-0.04, 0.04))
            if k == 0:
                d = (c - p).length
                if d > 1e-6:
                    q = q + (c - p) / d * min(taper, 0.35 * d)
            z = h * zf(s) * (1 + rng.uniform(-0.06, 0.04))
            if kind == "flat":
                d = (q - peak).dot(AWAY)
                z = min(z, h - 0.32 * max(d, -3) + rng.uniform(-0.25, 0.25))
            pts.append((q.x, q.y, max(z, 0.3)))
    if crest:
        a, b = crest
        for t, f in ((0.0, 0.92), (0.35, 1.0), (0.65, 0.99), (1.0, 0.9)):
            c = a + (b - a) * t
            pts.append((c.x, c.y, h * f))
    elif kind == "flat":
        def plane(q):
            return h - 0.32 * max((q - peak).dot(AWAY), -3)
        pts.append((peak.x, peak.y, plane(peak) + 0.6))
        for k in range(5):
            a = 2 * math.pi * k / 5 + rng.uniform(-0.2, 0.2)
            q = peak + Vector((math.cos(a), math.sin(a))) * rng.uniform(1.2, 1.7)
            pts.append((q.x, q.y, plane(q) + 0.35))
    else:
        r = min(1.2, 0.3 * h)
        for k in range(5):
            a = 2 * math.pi * k / 5 + rng.uniform(0, 1)
            pts.append((peak.x + r * math.cos(a), peak.y + r * math.sin(a), h * rng.uniform(0.95, 1.0)))
    # the belly: a rounded, closed underside (the heap drifts in an asteroid field)
    cx = sum(x for x, _ in foot) / len(foot)
    cy = sum(y for _, y in foot) / len(foot)
    for s, zf_ in ((0.3, -0.18), (0.62, -0.32)):
        for j in range(0, len(foot), 2):
            x, y = foot[j]
            pts.append((x + (cx - x) * s, y + (cy - y) * s, h * zf_ * rng.uniform(0.9, 1.05)))
    pts.append((cx, cy, -0.38 * h))
    return pts


def hull_object(name, pts, mat_index, mats, coll):
    bm = bmesh.new()
    verts = [bm.verts.new(Vector(p) * PX) for p in pts]
    res = bmesh.ops.convex_hull(bm, input=verts, use_existing_faces=False)
    drop = [v for v in res["geom_interior"] + res["geom_unused"] if isinstance(v, bmesh.types.BMVert)]
    bmesh.ops.delete(bm, geom=list(set(drop)), context="VERTS")
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(6.0), verts=bm.verts[:], edges=bm.edges[:])
    for f in bm.faces:
        f.material_index = mat_index
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    return o


def offset_poly(poly, d):
    n = len(poly)
    out = []
    for i in range(n):
        a, b, c = Vector(poly[i - 1]), Vector(poly[i]), Vector(poly[(i + 1) % n])

        def nrm(p, q):
            t = (q - p).normalized()
            return Vector((-t.y, t.x))
        m = nrm(a, b) + nrm(b, c)
        m = m.normalized() if m.length > 1e-6 else nrm(a, b)
        turn = (b - a).x * (c - b).y - (b - a).y * (c - b).x
        miter = 1.0 / max(m.dot(nrm(a, b)), 0.7) if turn < -1e-6 else 1.0
        out.append(tuple(b + m * d * miter))
    return out


def prism_object(name, poly, coll, profile=CLIP_PROFILE):
    area = sum(poly[i - 1][0] * poly[i][1] - poly[i][0] * poly[i - 1][1] for i in range(len(poly)))
    if area < 0:
        poly = poly[::-1]
    bm = bmesh.new()
    rings = [[bm.verts.new((x * PX, y * PX, z * PX)) for x, y in offset_poly(poly, d)] for z, d in profile]
    n = len(poly)
    for lo, hi in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    return o


def apply_mods(obj):
    bpy.context.view_layer.update()
    for o in bpy.context.view_layer.objects:
        if o is not None:
            o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    for mod in list(obj.modifiers):
        bpy.ops.object.modifier_apply(modifier=mod.name)


def boolean(obj, other, op):
    keep = obj.data.copy()
    for solver in ("EXACT", "MANIFOLD", "FLOAT"):
        mod = obj.modifiers.new(op, "BOOLEAN")
        mod.operation = op
        mod.solver = solver
        mod.object = other
        apply_mods(obj)
        if len(obj.data.polygons) > 0:
            if solver != "EXACT":
                print(f"A: {obj.name} boolean {op} fell back to {solver}")
            break
        obj.data = keep.copy()


def chamfer(obj, width=CHAMFER):
    mod = obj.modifiers.new("chamfer", "BEVEL")
    mod.width = width * PX
    mod.segments = 1
    mod.limit_method = "ANGLE"
    mod.angle_limit = math.radians(15)
    mod.use_clamp_overlap = True
    apply_mods(obj)


def build(name, coll):
    spec = MODELS[name]
    idx, colors = SM.load(name)
    m = SM.masks(idx, colors)
    inner = m["inner"]
    cells = spec["cells"]
    lab = label_cells(inner, cells)
    sprite = {"name": name, "colors": {str(k): list(v) for k, v in colors.items()}}
    pal = [cell_colour(idx, colors, lab, i) for i in range(len(cells))]
    used = sorted(set(pal))
    tag = name.replace("-", "")
    mats = [common.palette_material(sprite, i, tag, metallic=0.0, roughness=0.85) for i in used]
    rng = random.Random(spec["seed"])
    def grown(poly):
        poly = list(poly)
        for col, row in spec.get("extra", []):
            q = cr(col, row)
            best = min(range(len(poly)), key=lambda i: (nearest_on_seg(q, Vector(poly[i - 1]), Vector(poly[i])) - q).length)
            if (nearest_on_seg(q, Vector(poly[best - 1]), Vector(poly[best])) - q).length < 1.0:
                poly.insert(best, (q.x, q.y))
        if not spec.get("grow"):
            return poly
        area = sum(poly[i - 1][0] * poly[i][1] - poly[i][0] * poly[i - 1][1] for i in range(len(poly)))
        p = poly if area > 0 else poly[::-1]
        # out, but never past the tile's edges
        return [(min(max(x, -W / 2), W / 2), min(max(y, -H / 2), H / 2)) for x, y in offset_poly(p, -spec["grow"])]
    clip = prism_object("clip", grown(simplify(outline_poly(trace(inner)), CLIP_TOL)), coll,
                        profile=spec["clip"])
    rocks = []
    for i, cell in enumerate(cells):
        mask = [[lab[y][x] == i for x in range(W)] for y in range(H)]
        foot = grown(simplify(outline_poly(trace(mask)), FOOT_TOL))
        o = hull_object(f"rock_{cell['name']}", boulder_points(foot, cell, rng, spec['taper']), used.index(pal[i]), mats, coll)
        chamfer(o, CHAMFER if len(cells) > 1 else 0.2)
        boolean(o, clip, "INTERSECT")
        for f in o.data.polygons:
            f.material_index = used.index(pal[i])
        rocks.append(o)
        print(f"A: {name} {cell['name']}: pal {pal[i]}, {sum(map(sum, mask))} px, h {cell['h']}")
    bpy.data.objects.remove(clip, do_unlink=True)
    bm = bmesh.new()
    for o in rocks:
        b1 = bmesh.new()
        b1.from_mesh(o.data)
        bmesh.ops.remove_doubles(b1, verts=b1.verts[:], dist=1e-5)
        bmesh.ops.dissolve_degenerate(b1, dist=1e-5, edges=b1.edges[:])
        bmesh.ops.recalc_face_normals(b1, faces=b1.faces[:])
        nm = sum(1 for e in b1.edges if not e.is_manifold)
        print(f"A: {o.name} faces {len(b1.faces)} non-manifold edges {nm}")
        b1.to_mesh(o.data)
        b1.free()
        bm.from_mesh(o.data)
    for o in rocks:
        bpy.data.objects.remove(o, do_unlink=True)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for mt in mats:
        me.materials.append(mt)
    for poly in me.polygons:
        poly.use_smooth = False
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    return obj, m, {c["name"]: p for c, p in zip(cells, pal)}


# --- bake (assembly-newshd-89.py bake_piece, trimmed: no piece-box caps) ----------------------------

def set_engine(name):
    scene = bpy.context.scene
    try:
        scene.render.engine = name
    except TypeError as err:
        scene.render.engine = next(e for e in str(err).replace("'", " ").replace(",", " ").split() if name in e)


def bake_piece(obj, out_dir, size=256):
    me = obj.data
    uv = me.uv_layers.new(name="bake")
    me.uv_layers.active = uv
    bpy.context.view_layer.update()
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.01, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.006)
    bpy.ops.object.mode_set(mode="OBJECT")
    used = sorted({p.material_index for p in me.polygons})
    for k in used:
        c = me.materials[k].copy()
        c.name = f"{me.materials[k].name}"
        me.materials[k] = c
    mats = [me.materials[k] for k in used]
    col_img = bpy.data.images.new(f"{obj.name}_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new(f"{obj.name}_rm", size // 2, size // 2, alpha=False)
    rm_img.colorspace_settings.name = "Non-Color"
    saved = {}
    for mt in mats:
        out = next(n for n in mt.node_tree.nodes if n.type == "OUTPUT_MATERIAL")
        saved[mt.name] = out.inputs["Surface"].links[0].from_socket if out.inputs["Surface"].links else None

    def bake_shader(mt, mode):
        nt = mt.node_tree
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
        ao_s.samples = 16
        ao_s.inputs["Distance"].default_value = 0.05
        ao_l = node("ShaderNodeAmbientOcclusion")
        ao_l.samples = 16
        ao_l.inputs["Distance"].default_value = 0.3
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
                     math_("ADD", 0.6, math_("MULTIPLY", ao_l.outputs["AO"], 0.4)))
        em = node("ShaderNodeEmission")
        if mode == "colour":
            v = math_("MINIMUM", math_("ADD", math_("ADD", 0.42, math_("MULTIPLY", occl, 0.66)),
                                       math_("MULTIPLY", edge, 0.18)), 1.0)
            nt.links.new(v, em.inputs["Color"])
        else:
            r = math_("ADD", rough, math_("SUBTRACT", math_("MULTIPLY", math_("SUBTRACT", 1.0, occl), 0.15),
                                          math_("MULTIPLY", edge, 0.12)))
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
        tmps = {mt.name: bake_shader(mt, mode) for mt in mats}
        bpy.ops.object.bake(type="EMIT", margin=4, use_clear=True)
        for mt in mats:
            nt = mt.node_tree
            for n in tmps[mt.name]:
                nt.nodes.remove(n)
            out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
            if saved[mt.name] is not None:
                nt.links.new(saved[mt.name], out.inputs["Surface"])
        img.filepath_raw = str(Path(out_dir) / f"{img.name}.png")
        img.file_format = "PNG"
        img.save()
    for mt in mats:
        nt = mt.node_tree
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


# --- review renders --------------------------------------------------------------------------------

def setup_workbench(flat):
    scene = bpy.context.scene
    set_engine("BLENDER_WORKBENCH")
    sh = scene.display.shading
    sh.light = "FLAT" if flat else "STUDIO"
    sh.color_type = "MATERIAL"
    sh.show_cavity = not flat
    sh.show_object_outline = not flat
    sh.show_shadows = False
    scene.view_settings.view_transform = "Standard"
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"


def setup_game():
    scene = bpy.context.scene
    set_engine("BLENDER_EEVEE")
    world = scene.world or bpy.data.worlds.new("game")
    scene.world = world
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.42, 0.45, 0.55, 1.0)
    bg.inputs[1].default_value = 1.0
    sd = bpy.data.lights.new("game_sun", "SUN")
    sd.energy = 3.0
    sun = bpy.data.objects.new("game_sun", sd)
    bpy.context.scene.collection.objects.link(sun)
    d = Vector((-6, -8.4, 20)).normalized()
    sun.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    scene.view_settings.view_transform = "Standard"
    scene.render.film_transparent = True
    return sun


def camera(location, look_at, ortho=None, fov=None, top=False):
    data = bpy.data.cameras.new("cam")
    if ortho:
        data.type = "ORTHO"
        data.ortho_scale = ortho
    elif fov:
        data.sensor_fit = "VERTICAL"
        data.angle_y = math.radians(fov)
    cam = bpy.data.objects.new("cam", data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = location
    cam.rotation_euler = (0, 0, 0) if top else (Vector(look_at) - Vector(location)).to_track_quat("-Z", "Y").to_euler()
    return cam


def render(cam, path, rx, ry):
    scene = bpy.context.scene
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = rx, ry
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    data = cam.data
    bpy.data.objects.remove(cam, do_unlink=True)
    bpy.data.cameras.remove(data)


def workbench_colours(objs):
    for o in objs:
        for mt in o.data.materials:
            if not mt.node_tree:
                continue
            bsdf = next((n for n in mt.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
            if bsdf is None:
                continue
            base = bsdf.inputs["Base Color"]
            col = base.links[0].from_node.inputs[7].default_value if base.is_linked else base.default_value
            mt.diffuse_color = tuple(col)


def render_views(obj, hide, out, k=24, panel=420):
    out.mkdir(parents=True, exist_ok=True)
    for o in hide:
        o.hide_render = True
    workbench_colours([obj])
    obj.hide_render = False
    ext = H * PX
    # centre the oblique views on the rock itself, not the tile
    bb = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    c = Vector((sum(v.x for v in bb) / 8, sum(v.y for v in bb) / 8, 0.15))
    setup_workbench(True)
    render(camera((0, 0, 20), (0, 0, 0), ortho=ext, top=True), out / "top_flat.png", W * k, H * k)
    setup_workbench(False)
    render(camera((0, 0, 20), (0, 0, 0), ortho=ext, top=True), out / "top.png", W * k, H * k)
    span = ext * 1.15
    zc = 0.05
    render(camera((c.x - 30, c.y, zc), (c.x, c.y, zc), ortho=span), out / "left.png", 2 * panel, panel)
    render(camera((c.x + 30, c.y, zc), (c.x, c.y, zc), ortho=span), out / "right.png", 2 * panel, panel)
    render(camera((c.x, c.y + 30, zc), (c.x, c.y, zc), ortho=span), out / "front.png", 2 * panel, panel)
    render(camera((c.x, c.y - 30, zc), (c.x, c.y, zc), ortho=span), out / "rear.png", 2 * panel, panel)
    cu = camera((0, 0, -20), (0, 0, 0), ortho=ext, top=True)
    cu.rotation_euler = (math.pi, 0, 0)
    render(cu, out / "under.png", W * k // 2, H * k // 2)
    d = 3.2
    sun = setup_game()
    render(camera((c.x - d * 0.6, c.y - d * 0.55, d * 0.6), c, fov=35), out / "q34_fl.png", panel, panel)
    render(camera((c.x + d * 0.6, c.y + d * 0.55, d * 0.6), c, fov=35), out / "q34_rr.png", panel, panel)
    render(camera((c.x - d * 0.25, c.y - d * 0.15, d * 1.05), c, fov=35), out / "high.png", panel, panel)
    tilt = math.radians(32)
    render(camera((0, -d * math.sin(tilt), d * math.cos(tilt)), (0, 0, 0), fov=35), out / "game.png", panel, panel)
    bpy.data.objects.remove(sun, do_unlink=True)
    setup_workbench(True)
    saved = [tuple(mt.diffuse_color) for mt in obj.data.materials]
    for mt in obj.data.materials:
        mt.diffuse_color = (1, 1, 1, 1)
    render(camera((0, 0, 20), (0, 0, 0), ortho=ext, top=True), out / "top_mask.png", W * k, H * k)
    for mt, s in zip(obj.data.materials, saved):
        mt.diffuse_color = s
    for o in hide:
        o.hide_render = False


HEAP = ["newshd-13", "newshd-49", "newshd-51", "newshd-53", "newshd-89", "newshd-91"]
HEAP_LAYOUT = {"newshd-13": (146, 85), "newshd-53": (170, 113), "newshd-91": (170, 141), "newshd-89": (146, 141),
               "newshd-51": (146, 113), "newshd-49": (122, 113)}
PLACE = {"newshd-31": (128, 92), "newshd-15": (164, 92)}  # each filler's tile centre in the heap's frame


def render_context(objs, out, panel=640):
    """The fillers in place at the heap's two top corners, beside the published heap pieces."""
    out.mkdir(parents=True, exist_ok=True)
    cx0, cy0 = 146, 113
    heap = []
    for name in HEAP:
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=str(WT / "public" / "models" / "enemies" / f"{name}.glb"))
        new = [o for o in bpy.data.objects if o not in before]
        x, y = HEAP_LAYOUT[name]
        for o in new:
            if o.parent is None:
                o.location = ((x - cx0) / 12, -(y - cy0) / 12, 0)
            if o.get("tyrian_outline"):
                o.hide_render = True
        heap += new
    for name, o in objs.items():
        x, y = PLACE[name]
        o.location = ((x - cx0) / 12, -(y - cy0) / 12, 0)
    workbench_colours([o for o in heap if o.type == "MESH" and not o.get("tyrian_outline")] + list(objs.values()))
    sun = setup_game()
    tilt = math.radians(32)
    d = 13.0
    look = Vector((0, 0.3, 0))
    render(camera((look.x, look.y - d * math.sin(tilt), d * math.cos(tilt)), look, fov=35), out / "ctx_game.png", panel, panel)
    for nm, (x, y) in PLACE.items():  # the same tilt, zoomed on each filler
        p = Vector(((x - cx0) / 12, -(y - cy0) / 12, 0.2))
        render(camera((p.x, p.y - d * math.sin(tilt), d * math.cos(tilt)), p, fov=9), out / f"ctx_gamezoom_{nm}.png", panel, panel)
    render(camera((look.x - 2.2, look.y - 1.2, 3.2), (-1.5, 1.7, 0.3), fov=35), out / "ctx_q34_31.png", panel, panel)
    render(camera((look.x + 3.6, look.y - 1.2, 3.2), (1.5, 1.7, 0.3), fov=35), out / "ctx_q34_15.png", panel, panel)
    render(camera((-1.5, 6, 2.6), (-1.0, 1.7, 0.3), fov=30), out / "ctx_back_31.png", panel, panel)
    bpy.data.objects.remove(sun, do_unlink=True)
    setup_workbench(False)
    render(camera((0, 0, 20), (0, 0, 0), ortho=7.6, top=True), out / "ctx_top.png", panel, panel)
    for o in heap:
        o.hide_render = True
    for o in objs.values():
        o.location = (0, 0, 0)


# --- main ------------------------------------------------------------------------------------------

def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    bpy.ops.wm.read_factory_settings(use_empty=True)
    coll = common.reset_collection("newshd-31_A")
    objs, shells, masks = {}, {}, {}
    for name in ("newshd-31", "newshd-15"):
        obj, m, pal = build(name, coll)
        print(f"A: {name} palette per boulder {pal}")
        objs[name], masks[name] = obj, m
        bpy.context.view_layer.update()
        shells[name] = common.outline_shell(obj, coll, voxel=0.008, faces=1200, smooth=3)
    fmt = "AUTO"
    if "--no-bake" not in argv:
        scene = bpy.context.scene
        set_engine("CYCLES")
        scene.cycles.samples = 48
        scene.cycles.device = "CPU"
        tmp = tempfile.mkdtemp(prefix="nshd31A_bake_")
        for sh in shells.values():
            sh.hide_render = True
        for i, (name, o) in enumerate(objs.items()):
            for other in objs.values():
                other.hide_render = other is not o
            bake_piece(o, tmp)
        for o in objs.values():
            o.hide_render = False
        fmt = "WEBP"
    if "--render" in argv:
        base = Path(argv[argv.index("--render") + 1])
        for name, o in objs.items():
            others = [x for n, x in objs.items() if n != name] + list(shells.values())
            render_views(o, others, base / name)
            top = SM.read_png_mask(str(base / name / "top_mask.png"))
            res = SM.measure(masks[name], top)
            print(f"A: {name} IoU rule grid {res['iou_rule_grid']} rule {res['iou_rule']} "
                  f"inner {res['iou_inner']} outer {res['iou_outer']}")
    if "--context" in argv:
        for sh in shells.values():
            sh.hide_render = True
        render_context(objs, Path(argv[argv.index("--context") + 1]))
    for name, o in objs.items():
        o.location = (0, 0, 0)
        shells[name].location = (0, 0, 0)
        common.export_sprite_model(WT, [o, shells[name]], f"enemies/{name}",
                                   common.load_sprite(WT, name)["sprites"], image_format=fmt)


if __name__ == "__main__":
    main()
