"""Big asteroid (newshd 7 / 9 / 45 / 47, one 48 x 56 cell): a boulder of fractured stones, on the
D125 rock builder (lib_newshd_rock) so it reads as the same stone as the episode's other asteroids.

Reading the sprite: a grey boulder of eight fractured stones split by dark cracks (blueprint
../blueprint/blueprint.png): a big pale flat-topped stone on the upper left ("facet"), a knob on
top, a ridged crown on the upper right, a small slab in the middle with a white lit edge, a dark
flank on the right, a rounded stone on the lower left with a lit ridge, one on the lower right and
a dark keel along the bottom. Bright pixels are lit faces (rock, rubric), the black ring is the
game's ink (D74), so nothing of either is painted or modelled.

Build (D125, QA2 issue 13: the earlier cluster of convex hulls read as grey plastic beside the D125
asteroids): ONE rock body lofted from the cell's inner mask (lib_newshd_rock.rock_body: round all
over, a closed domed underside, no base), its top raised into the stones the sprite draws (a bump
per stone, the big pale facet the summit) and sunk along the cracks between them (valleys, with V
crack grooves cut along the deep ones), then broken by the builder's planar fracture faces, fine
cuts, rim spalls and a few impact pits on the sprite's dark spots; chamfered fracture edges, smooth
weathered body. Matte stone (metallic 0, roughness 0.9) and the builder's AO/roughness bake
(usp_talon.bake_maps, no concept projection, D50/D65), D90 outline shell from a sealed copy kept
out of the bake (D118). Colour per stone: the trimmed median of the sprite's ramp in that stone
(its ink ring, dark limb and glints are lighting).

Pieces: built whole, cut with common.split_assembly into newshd-7 (top left), -9 (top right), -45
(bottom left), -47 (bottom right), one frame each, each with its slice of the outline shell (cut
open, as assembly-newshe-39 does, so no ink line runs along the seams).

Run: blender -b --factory-startup -P assets/blender/enemies/assembly-newshd-45.py [-- --no-bake] [--review DIR]
(exports the four pieces to public/models/enemies and src/render/spriteModels; --review DIR also writes
the cell .glb with the pieces placed, for the review renders).
"""

import json
import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import common  # noqa: E402
import lib_newshd_rock as lib  # noqa: E402
import usp_talon as T  # noqa: E402

WT = common.repo_root(__file__)
sys.path.insert(0, str(WT / "tools"))
import sprite_mask  # noqa: E402

NAME = "assembly-newshd-45"
PIECES = ["newshd-7", "newshd-9", "newshd-45", "newshd-47"]
CENTRE = (94, -2)
W, H = 48, 56
U = 1 / 12

# Seed polygons along the sprite's cracks (sprite px, x right, y down); from the blueprint's prep.py.
# The facet stone's cracks, along the sprite's darkest pixels (they wander about a pixel; a straight
# seed edge here made the top view read as a 2 x 2 grid of blocks):
#   VCRACK  facet / knob + crown, top to bottom (rows 11-22: darkest column per row)
#   SCRACK  facet / slab, down to the junction with the lower stones
#   HCRACK  facet / lower-left, right to left (columns 13-26: darkest row per column)
VCRACK = [(27, 11), (27.6, 13.4), (28.5, 15.1), (28.2, 16.6), (29.1, 18.0), (29.9, 19.5), (29.4, 21.0), (28.3, 22.3)]
SCRACK = [(28.3, 22.3), (27.6, 24.0), (27.4, 26.4), (26.6, 28.4), (26.5, 30.8)]
HCRACK = [(26.5, 30.8), (25.0, 31.5), (23.5, 31.0), (21.5, 31.0), (19.6, 30.1), (17.6, 31.2), (15.6, 30.9),
          (13.6, 30.3), (8, 29)]

SEEDS = {
    "knob":      [(25, 2), (40, 2), (42, 8.5), (37, 12), (31, 12.5), (27, 11)],
    "crown":     [(27, 11), (31, 12.5), (37, 12), (42, 8.5), (48, 9), (48, 21), (42, 22.5), (36.5, 23.5), (31, 21.5),
                  (28.3, 22.3)] + VCRACK[::-1][1:-1],
    "facet":     [(8, 9), (27.5, 9)] + VCRACK + SCRACK[1:] + HCRACK[1:],
    "slab":      [(28.3, 22.3), (31, 21.5), (36.5, 23.5), (36, 27.5), (35, 31.5), (30, 30.8)] + SCRACK[::-1][:-1],
    "flank":     [(36.5, 23.5), (42, 22.5), (48, 21), (48, 34), (41, 32.5), (35, 31.5), (36, 27.5)],
    "lowerleft": [(0, 28)] + HCRACK[::-1] + [(29.5, 36), (27, 42.8), (24, 43.5), (12, 42), (0, 39)],
    "lowerright": [(26.5, 30.8), (30, 30.8), (35, 31.5), (41, 32.5), (48, 34), (48, 39), (36, 41), (27, 42.8), (29.5, 36)],
    # the blueprint's keel, split at the dark crack below the lower stones (x 24-26, y 43-48)
    "keelL":     [(0, 39), (12, 42), (24, 43.5), (25.5, 48), (26, 60), (0, 60)],
    "keelR":     [(24, 43.5), (27, 42.8), (36, 41), (48, 39), (48, 60), (26, 60), (25.5, 48)],
}


# Each stone is a small D125 rock (lib_newshd_rock: a body lofted from its own region of the inner
# mask, round all over, its top raised to a summit and crests, broken by planar fracture faces,
# fine cuts and rim spalls, a few pits). Per stone (sprite px unless said):
#   h, depth   height of its summit above the waist / depth of its underside below it; the stones
#              fall away towards the rock's rim (the boulder's dome) and the facet and slab stand
#              highest, as the sprite lights them
#   summit     where its top peaks: the lit point the sprite draws on it, near the region's middle
#   crests     lit streaks: ((col, row), (col, row), gain, width)
#   bumps      ((col, row), gain, radius): the facet's broad pale face, the shadowed sides
#   zw         its waist's height (px), so the waists don't line up into one belt in the side views
#   pits       the sprite's dark spots on it ((col, row), radius in units)
STONES = {
    "knob":       dict(h=9.0, depth=7.0, seed=3, zw=0.6, summit=(33.5, 7.5),
                       crests=[((32.5, 6.0), (36.5, 10.0), 0.10, 1.2)]),
    "crown":      dict(h=10.5, depth=9.5, seed=5, zw=-0.4, summit=(38.0, 15.0),
                       crests=[((37.0, 12.5), (34.5, 20.0), 0.12, 1.2)], pits=[((42.5, 16.0), 0.05)]),
    "facet":      dict(h=12.0, depth=10.5, seed=7, zw=-0.6, summit=(21.5, 19.0), top_pow=0.45,
                       crests=[((22.5, 15.5), (27.0, 21.0), 0.08, 1.4)],
                       bumps=[((22.0, 24.0), 0.08, 4.0), ((13.0, 21.0), -0.12, 3.0), ((19.0, 13.0), -0.10, 2.6)]),
    "slab":       dict(h=12.5, depth=9.5, seed=11, zw=0.4, summit=(31.0, 26.0),
                       crests=[((29.5, 23.5), (29.5, 29.5), 0.10, 1.0)], pits=[((34.0, 28.5), 0.05)]),
    "flank":      dict(h=8.5, depth=9.0, seed=13, zw=-0.2, summit=(40.0, 27.0),
                       crests=[((40.5, 24.5), (39.5, 30.5), 0.08, 1.2)], pits=[((37.5, 28.5), 0.06)]),
    "lowerleft":  dict(h=11.0, depth=10.5, seed=17, zw=0.8, summit=(19.0, 36.0),
                       crests=[((20.0, 32.5), (17.5, 39.5), 0.12, 1.2)]),
    "lowerright": dict(h=10.0, depth=9.5, seed=19, zw=-0.8, summit=(35.0, 36.0),
                       crests=[((35.0, 33.5), (33.0, 38.5), 0.10, 1.2)], pits=[((40.0, 35.5), 0.06)]),
    "keelL":      dict(h=6.5, depth=8.5, seed=23, zw=-0.3, summit=(16.0, 45.0),
                       crests=[((12.5, 42.5), (20.0, 45.0), 0.08, 1.4)], pits=[((20.5, 47.5), 0.06)]),
    "keelR":      dict(h=5.5, depth=8.5, seed=29, zw=0.2, summit=(33.0, 45.0),
                       crests=[((29.0, 45.5), (36.0, 43.5), 0.08, 1.4)]),
}

# Shared by every stone (lib_newshd_rock SPEC keys; D125's matte stone).
BASE = {
    "metallic": 0.0,
    "roughness": 0.9,
    "rise": 0.7,
    "fall": 0.8,
    "sectors": 40,
    "rings_top": 10,
    "rings_bot": 5,
    "summit_gain": 0.06,
    "summit_r": 2.4,
    "ridges": [],
    "valleys": [],
    "tilt": 0.02,
    "lumps": 0.03,
    "grow": 0.1,
    "smooth": 1,
    "steps": 64,
    "waist": 0.08,
    "fine": 14,
    "fine_depth": (0.025, 0.045),
    "rim_spalls": 10,
    "rim_depth": (0.02, 0.035),
    "cuts": [
        # a couple of near-level faces so the crown never closes to a point
        (160, 78, 0.035), (20, 80, 0.03), (270, 82, 0.03),
        # lit faces turned to the light (left / upper-left / lower-left)
        (150, 46, 0.07), (205, 44, 0.06), (125, 56, 0.05), (232, 52, 0.05),
        # the shadowed right, upper-right and lower-right
        (10, 46, 0.07), (60, 54, 0.05), (330, 46, 0.06), (290, 58, 0.05),
        # underside: a few planes so it reads as stone, nothing more
        (30, -55, 0.05), (150, -50, 0.05), (260, -58, 0.05), (100, -30, 0.03), (320, -26, 0.03),
    ],
    "pit_lift": 0.55,
}
CRACK_GROW = 1  # px each stone's region is grown into its neighbours: the stones overlap, so each
                # crack is a V groove where two stones meet, never a hole

# D90's outline shell, a little denser and held further inside for this big rock (3000 faces over
# the cell; inside 0.012 so it never stands over the shallow V cracks)
SHELL = dict(lib.D90_SHELL, faces=3000, inside=0.012)

# The facet's median falls exactly on the 9/10 step (117th of 234 body pixels) and 10 is its most
# common colour (65 px): the big pale face is 10, as the blueprint measured it.
PAL_OVERRIDE = {"facet": 10}

LABELS = {}  # the stone labels and palette indices, written next to the review glb

# --- sprite --------------------------------------------------------------------------------------

def sprite():
    idx, colors = sprite_mask.load(NAME)
    m = sprite_mask.masks(idx, colors)
    return idx, {str(k): list(v) for k, v in colors.items()}, m["inner"]


def inside(poly, x, y):
    n, c = len(poly), False
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


def labels(idx):
    names = list(SEEDS)
    cents = {n: (sum(p[0] for p in SEEDS[n]) / len(SEEDS[n]), sum(p[1] for p in SEEDS[n]) / len(SEEDS[n]))
             for n in names}
    lab = [[-1] * W for _ in range(H)]
    for y in range(H):
        for x in range(W):
            if idx[y][x] < 0:
                continue
            for i, n in enumerate(names):
                if inside(SEEDS[n], x + 0.5, y + 0.5):
                    lab[y][x] = i
                    break
            else:
                lab[y][x] = min(range(len(names)),
                                key=lambda i: math.hypot(cents[names[i]][0] - x - .5, cents[names[i]][1] - y - .5))
    return names, lab


def region_pal(idx, colors, lab, i, inner):
    """The stone's palette index: median by luminance of its pixels on the D74 inner mask (the ink ring
    is outside it), the darkest 15 % and brightest 15 % (shading and lit faces) dropped."""
    lum = lambda v: sum(colors[str(v)]) / 3  # noqa: E731
    vals = [idx[y][x] for y in range(H) for x in range(W) if lab[y][x] == i and inner[y][x] and idx[y][x] not in (-1, 1, 3, 32)]
    vals.sort(key=lum)
    k = len(vals) * 15 // 100
    keep = vals[k:len(vals) - k] or vals
    return keep[len(keep) // 2]


# --- the stones ----------------------------------------------------------------------------------

class StoneGrid(lib.Grid):
    """lib_newshd_rock's sprite grid over the 48 x 56 cell, its mask one stone's region."""

    def __init__(self, mask):
        self.w, self.h = W, H
        self.inner = mask


def stone_mask(lab, i, inner, grow):
    """The stone's region of the inner mask, grown `grow` px (8-neighbour) into its neighbours but
    never past the rock's edge."""
    m = [[lab[y][x] == i and inner[y][x] for x in range(W)] for y in range(H)]
    for _ in range(grow):
        m = [[inner[y][x] and any(0 <= y + dy < H and 0 <= x + dx < W and m[y + dy][x + dx]
                                  for dy in (-1, 0, 1) for dx in (-1, 0, 1)) for x in range(W)] for y in range(H)]
    return m


def stone(name, mask, spr, pal, coll):
    """One stone: lib_newshd_rock's loft, fracture cuts and pits on its own region."""
    p = STONES[name]
    spec = dict(BASE, seed=p["seed"], summit=p["summit"], h_top=p["h"] / 12, h_bot=p["depth"] / 12,
                crests=p.get("crests", []), bumps=p.get("bumps", []))
    if "top_pow" in p:
        spec["top_pow"] = p["top_pow"]
    g = StoneGrid(mask)
    bm, _ = lib.rock_body(g, spec, sectors=spec["sectors"], rings_top=spec["rings_top"], rings_bot=spec["rings_bot"])
    lib.cut_planes(bm, spec["cuts"] + lib.fine_cuts(spec))
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges[:], dist=1e-5)
    bmesh.ops.translate(bm, vec=(0, 0, p["zw"] / 12), verts=bm.verts)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    mat = common.palette_material(spr, pal, NAME, metallic=BASE["metallic"], roughness=BASE["roughness"])
    obj = common.mesh_object(f"{NAME}_{name}", bm, [mat], coll, smooth=True)
    pits = p.get("pits", [])
    if pits:
        bvh = BVHTree.FromObject(obj, bpy.context.evaluated_depsgraph_get())
        for k, ((u, v), r) in enumerate(pits):
            hit = bvh.ray_cast(Vector((g.x(u), g.y(v), 5.0)), Vector((0, 0, -1)))
            if hit[0] is None:
                continue
            cb = bmesh.new()
            bmesh.ops.create_uvsphere(cb, u_segments=12, v_segments=7, radius=r)
            c = hit[0] + hit[1] * r * BASE["pit_lift"]
            bmesh.ops.scale(cb, vec=(1, 1, 0.75), verts=cb.verts)
            bmesh.ops.translate(cb, vec=c, verts=cb.verts)
            lib.boolean(obj, cb, f"pit_{name}{k}")
        bpy.context.view_layer.update()
        while len(obj.data.materials) > 1:  # a cutter can leave an empty slot behind
            obj.data.materials.pop()
        obj.data.materials[0] = mat
        for f in obj.data.polygons:
            f.material_index = 0
    return obj


def build(coll):
    """The boulder: one D125 rock per stone, overlapping at the cracks, joined into one object
    with one palette material per stone; chamfered fracture edges, smooth weathered body."""
    idx, colors, inner = sprite()
    names, lab = labels(idx)
    spr = {"name": NAME, "colors": colors}
    pal, objs = {}, []
    for i, n in enumerate(names):
        if not any(lab[y][x] == i and inner[y][x] for y in range(H) for x in range(W)):
            continue
        pal[n] = PAL_OVERRIDE.get(n) or region_pal(idx, colors, lab, i, inner)
        objs.append(stone(n, stone_mask(lab, i, inner, CRACK_GROW), spr, pal[n], coll))
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    obj = objs[0]
    obj.name = obj.data.name = NAME
    # one slot per palette index (stones sharing a colour share the material)
    order = sorted(set(pal.values()))
    by_pal = {}
    for m in obj.data.materials:
        by_pal.setdefault(int(m.name.split("_")[1]), m)
    remap = [order.index(int(m.name.split("_")[1])) for m in obj.data.materials]
    face_mat = [remap[f.material_index] for f in obj.data.polygons]
    obj.data.materials.clear()  # (this resets the faces' indices, so they're set after)
    for p in order:
        obj.data.materials.append(by_pal[p])
    for f, k in zip(obj.data.polygons, face_mat):
        f.material_index = k
    bev = obj.modifiers.new("chamfer", "BEVEL")
    bev.width = 0.006
    bev.segments = 1
    bev.limit_method = "ANGLE"
    bev.angle_limit = math.radians(28)
    bpy.context.view_layer.update()
    common._apply_modifiers(obj)
    obj.data.shade_smooth()
    obj.data.set_sharp_from_angle(angle=math.radians(14))
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    open_edges = sum(1 for e in bm.edges if not e.is_manifold)
    bm.to_mesh(obj.data)
    bm.free()
    print("stone palette", pal)
    print(f"rock triangles {len(obj.data.polygons)}, non-manifold edges {open_edges}")
    LABELS.update(names=names, label=lab, pal=pal)
    return obj, pal

def split_open(obj, layout, coll):
    """common.split_assembly without filling the cuts, for the outline shells (assembly-newshe-39)."""
    out = {}
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)
        for co, no in (((x0 - 1, 0, 0), (-1, 0, 0)), ((x0 + 1, 0, 0), (1, 0, 0)),
                       ((0, y0 - 14 / 12, 0), (0, -1, 0)), ((0, y0 + 14 / 12, 0), (0, 1, 0))):
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co,
                                   plane_no=no, clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(f"{name}_outline")
        bm.to_mesh(me)
        bm.free()
        for m in obj.data.materials:
            me.materials.append(m)
        s = bpy.data.objects.new(f"{name}_outline", me)
        coll.objects.link(s)
        s.data.shade_smooth()
        s["tyrian_outline"] = True
        out[name] = s
    return out



def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    bpy.ops.wm.read_factory_settings(use_empty=True)
    coll = common.reset_collection(NAME)
    obj, pal = build(coll)
    # the shell's source: a sealed copy kept out of the scene while the bake runs (D118)
    closed = obj.copy()
    closed.data = obj.data.copy()
    fmt = "AUTO"
    if "--no-bake" not in argv:  # the D125 rocks' AO/roughness bake (no concept projection)
        tint, textured = T.TINT, T.TEXTURED
        T.TINT, T.TEXTURED = (1.0, 1.0, 1.0), tuple(range(len(obj.data.materials)))
        try:
            T.bake_maps(obj, tempfile.mkdtemp(prefix="nshd45_bake_"), size=1024, samples=64)
        finally:
            T.TINT, T.TEXTURED = tint, textured
        for img in bpy.data.images:
            if img.name.startswith("talon_"):
                img.name = img.name.replace("talon_", f"{NAME}_")
        fmt = "WEBP"
    coll.objects.link(closed)
    shell = common.outline_shell(closed, coll, **SHELL)
    bpy.data.objects.remove(closed)
    bpy.context.view_layer.update()
    first = common.load_sprite(WT, PIECES[0])
    layout = [(e["model"], e["cx"] - CENTRE[0], e["cy"] - CENTRE[1]) for e in first["assemblyLayout"]]
    pieces = common.split_assembly(obj, layout)
    for q in pieces.values():  # the filled cuts meet the surface at a hard edge: keep it out of the
        q.data.set_sharp_from_angle(angle=math.radians(14))  # smooth normals, so no seam line shows
    shells = split_open(shell, layout, coll)
    for name, cx, cy in layout:
        print(f"{name}: {sum(len(q.vertices) - 2 for q in pieces[name].data.polygons)} triangles")
    if "--review" in argv:  # the cell with the pieces placed, for the review renders
        d = Path(argv[argv.index("--review") + 1])
        d.mkdir(parents=True, exist_ok=True)
        objs = []
        for name, cx, cy in layout:
            for o in (pieces[name], shells[name]):
                o.location = (cx / 12, -cy / 12, 0)
                objs.append(o)
        bpy.context.view_layer.update()
        common.export_glb(objs, d / "cell.glb", image_format=fmt)
        (d / "labels.json").write_text(json.dumps(LABELS))
        for o in objs:
            o.location = (0, 0, 0)
        bpy.context.view_layer.update()
    for name in PIECES:
        data = common.load_sprite(WT, name)
        common.export_sprite_model(WT, [pieces[name], shells[name]], f"enemies/{name}", data["sprites"], image_format=fmt)


if __name__ == "__main__":
    main()
