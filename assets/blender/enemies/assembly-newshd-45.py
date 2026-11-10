"""Big asteroid (newshd 7 / 9 / 45 / 47, one 48 x 56 cell), design B: a cluster of fractured stones.

Reading the sprite: a grey boulder of eight fractured stones split by dark cracks (blueprint
../blueprint/blueprint.png): a big pale flat-topped stone on the upper left ("facet"), a knob on
top, a ridged crown on the upper right, a small slab in the middle with a white lit edge, a dark
flank on the right, a rounded stone on the lower left with a lit ridge, one on the lower right and
a dark keel along the bottom. Bright pixels are lit faces (rock, rubric), the black ring is the
game's ink (D74), so nothing of either is painted or modelled.

Design B leads with the silhouette and the read from the small tilted camera: each stone is a
CONVEX HULL of jittered rings (its own footprint from the sprite at the waist, then shoulder,
crown and cap rings shrunk towards a peak set near its lit upper-left edge, and two underside
rings), planar-dissolved into a few big fracture facets and chamfered, flat shaded. Stones overlap
by about a pixel into their neighbours, so the cracks are V grooves where two hulls meet (the
rock's "panel lines"). The union of the waist footprints is the sprite's inner mask (the inner
edge of the ink border, D74), smoothed; only crack ends make the hulls a hair wider than a concave
footprint. Hard, fractured rock, no lumps for highlights. Underside: two shrinking rings per stone,
a closed blunt shape, no detail.

Pieces: built whole, cut with common.split_assembly into newshd-7 (top left), -9 (top right), -45
(bottom left), -47 (bottom right), one frame each, each with its slice of the outline shell (cut
open, as assembly-newshe-39 does, so no ink line runs along the seams). The design .glb holds the
four pieces placed in the cell (node translations) plus their shells.

Run: blender -b --factory-startup -P assets/blender/enemies/assembly-newshd-45.py [-- --no-bake] [--review DIR]
(exports the four pieces to public/models/enemies and src/render/spriteModels; --review DIR also writes
the cell .glb with the pieces placed, for the review renders).
"""

import json
import math
import random
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import common  # noqa: E402

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

# Per stone: height above the waist (sprite px), underside depth, seed, and the top's shape:
#   ridge: a fracture ridge (two sprite-px points) at the stone's height, set on the lit streak the
#          sprite draws (crown's diagonal ridge, slab's white edge, lower-left's bright ridge...): the
#          stone falls away from it in a few big planar faces, so the face turned to the light is a
#          narrow bright facet beside the ridge and the rest slopes into shade, as the sprite shades it.
#   tops:  the top's fracture points (x, y, z as a share of h) where one ridge can't place the facets:
#          the big pale facet stone. Its ridge runs from the upper left to the apex of the lit wedge the
#          sprite draws (x 21-28, y 15-28), then down the crack with the crown; the wedge is one gentle
#          face turned to the light below it, a crease down its left edge drops the pale rest to the
#          west (half lit), breaking steeper again at x 16.6 (the sprite's darker left edge), and the
#          strip above the ridge falls into shade to the north (the sprite's dark rows 12-14).
#   zw, wall: the waist's height and the rounded wall's top above it (share of h); the facet's are
#          low, so its west face drops steeply, half turned from the light.
#   bevel: chamfer width (sprite px); the facet's is narrower, so its edges read as fractures.
STONES = {
    "knob":       dict(h=11.0, depth=8.0, seed=3, ridge=((32.5, 6.5), (36.5, 10.0))),
    "crown":      dict(h=12.0, depth=11.0, seed=5, ridge=((37.0, 12.5), (34.5, 20.0))),
    "facet":      dict(h=12.0, depth=11.0, seed=7, bevel=0.18, zw=-0.8, wall=0.1,
                       tops=((16.5, 13.5, 0.32), (22.5, 15.5, 1.0), (27.2, 21.0, 0.95), (20.8, 27.2, 0.78),
                             (26.0, 28.0, 0.66), (23.5, 29.5, 0.45), (16.6, 18.5, 0.5), (16.9, 25.0, 0.46))),
    "slab":       dict(h=12.0, depth=10.0, seed=11, ridge=((31.0, 24.0), (30.5, 29.5))),
    "flank":      dict(h=9.0, depth=10.0, seed=13, ridge=((40.5, 24.5), (39.5, 30.5))),
    "lowerleft":  dict(h=11.0, depth=11.0, seed=17, ridge=((20.0, 32.0), (17.5, 39.5))),
    "lowerright": dict(h=10.0, depth=10.0, seed=19, ridge=((35.0, 33.5), (33.0, 38.5))),
    "keelL":      dict(h=8.0, depth=9.0, seed=23, ridge=((12.5, 42.5), (20.0, 45.0))),
    "keelR":      dict(h=6.5, depth=9.0, seed=29, ridge=((29.0, 45.5), (36.0, 43.5))),
}


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


def trace(mask):
    """Outer boundary of a binary region along pixel corners (longest loop), screen coords."""
    edges = {}
    for y in range(H):
        for x in range(W):
            if not mask[y][x]:
                continue
            g = lambda yy, xx: 0 <= yy < H and 0 <= xx < W and mask[yy][xx]  # noqa: E731
            if not g(y - 1, x):
                edges[(x + 1, y)] = (x, y)
            if not g(y, x - 1):
                edges[(x, y)] = (x, y + 1)
            if not g(y + 1, x):
                edges[(x, y + 1)] = (x + 1, y + 1)
            if not g(y, x + 1):
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


def smooth_loop(loop, it=2):
    """Pixel staircase -> smooth closed curve: edge midpoints, then Chaikin corner cutting."""
    n = len(loop)
    pts = [((loop[i][0] + loop[(i + 1) % n][0]) / 2, (loop[i][1] + loop[(i + 1) % n][1]) / 2) for i in range(n)]
    for _ in range(it):
        q = []
        for i in range(len(pts)):
            a, b = pts[i], pts[(i + 1) % len(pts)]
            q += [(0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]), (0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1])]
        pts = q
    return pts


def resample(pts, step):
    """Even spacing of about `step` px along a closed polyline."""
    L = [0.0]
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        L.append(L[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    total = L[-1]
    n = max(8, int(round(total / step)))
    out, j = [], 0
    for k in range(n):
        t = total * k / n
        while L[j + 1] < t:
            j += 1
        a, b = pts[j], pts[(j + 1) % len(pts)]
        f = (t - L[j]) / max(1e-9, L[j + 1] - L[j])
        out.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
    return out


# --- stones --------------------------------------------------------------------------------------

def footprint(region, inner, grow=1.3, pull=-0.08):
    """The stone's waist outline (sprite px): its region's smoothed boundary, resampled; points
    on internal cracks pushed out `grow` px into the neighbours (the stones overlap there, so the
    crack is a V groove, never a hole), points on the rock's outer edge pulled `pull` px in."""
    pts = resample(smooth_loop(trace(region)), 1.6)
    n = len(pts)
    out, outer = [], []
    for i, (x, y) in enumerate(pts):
        a, b = pts[i - 1], pts[(i + 1) % n]
        tx, ty = b[0] - a[0], b[1] - a[1]
        L = math.hypot(tx, ty) or 1
        # outward normal of a loop that runs clockwise on screen (trace goes that way: top edge right->left...)
        nx, ny = ty / L, -tx / L
        cx = sum(p[0] for p in pts) / n
        cy = sum(p[1] for p in pts) / n
        if nx * (x - cx) + ny * (y - cy) < 0:
            nx, ny = -nx, -ny
        # outer: a pixel just outside along the normal is outside the rock
        o = False
        for d in (0.7, 1.4):
            px, py = int(math.floor(x + nx * d)), int(math.floor(y + ny * d))
            if not (0 <= px < W and 0 <= py < H) or not inner[py][px]:
                o = True
        if o:
            out.append((x - nx * pull, y - ny * pull))
        else:
            # push into the neighbour, but never out past the rock's edge (crack ends at the rim)
            for g in (grow, grow * 0.5, grow * 0.2, 0.0):
                qx, qy = x + nx * g, y + ny * g
                if all(0 <= int(qx + ex) < W and 0 <= int(qy + ey) < H and inner[int(qy + ey)][int(qx + ex)]
                       for ex, ey in ((0, 0), (0.6, 0), (-0.6, 0), (0, 0.6), (0, -0.6))):
                    break
            out.append((qx, qy))
        outer.append(o)
    return out, outer


def stone_points(name, fp, outer, p, G):
    """Hull points of one stone in sprite px (x right, y down, z up)."""
    rng = random.Random(p["seed"])
    n = len(fp)
    cx = sum(q[0] for q in fp) / n
    cy = sum(q[1] for q in fp) / n
    h, D = p["h"], p["depth"]

    def dome(x, y):
        """the whole rock is domed: stones fall away towards its rim, so it reads as one boulder"""
        r2 = ((x - G[0]) / 19.0) ** 2 + ((y - G[1]) / 25.0) ** 2
        return max(0.45, 1.12 - 0.5 * r2)

    # each stone's waist sits a little higher or lower (only x, y make the silhouette), so the
    # stones' waists don't line up into one seam round the rock in the side views
    zw = rng.uniform(-1.6, 1.6)
    zw = p.get("zw", zw)
    wall = p.get("wall", 0.22)  # the rounded wall's top above the waist (share of h)
    pts = []
    for (x, y), o in zip(fp, outer):
        if o:
            pts.append((x, y, zw + rng.uniform(-0.3, 0.3)))
            # rounded wall either side of the waist (a hair inside it), so the waist is no hard rim
            ix, iy = x + (cx - x) * 0.06, y + (cy - y) * 0.06
            pts.append((ix, iy, zw + wall * h * dome(x, y)))
            pts.append((ix, iy, zw - 0.18 * D))
        else:
            pts.append((x, y, 0.15 * h * dome(x, y)))
    if p.get("tops"):
        T = p["tops"]
        for x, y, zf in T:  # no dome here: the points place the facets' planes exactly
            pts.append((x, y, zf * h))
        # a chamfer band: the waist points pulled a little in and up towards the nearest top point,
        # so the walls round over into the top facets rather than ending in a rim
        off = rng.random()
        for k in range(8):
            x, y = fp[int((k + off) * n / 8) % n]
            qx, qy, qz = min(T, key=lambda t: (t[0] - x) ** 2 + (t[1] - y) ** 2)
            X, Y = qx + (x - qx) * 0.86, qy + (y - qy) * 0.86
            pts.append((X, Y, (wall + 0.03) * h * dome(X, Y)))
    else:
        (ax, ay), (bx, by) = p["ridge"]

        def near(x, y):
            dx, dy = bx - ax, by - ay
            t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)))
            return ax + dx * t, ay + dy * t

        # a few big fracture faces: a band of 8 points, an upper ring of 5, the ridge
        for count, s_, zf in ((8, 0.86, 0.48), (5, 0.52, 0.8)):
            off = rng.random()
            for k in range(count):
                x, y = fp[int((k + off) * n / count) % n]
                qx, qy = near(x, y)
                sj = s_ * (1 + rng.uniform(-0.07, 0.05))
                X, Y = qx + (x - qx) * sj, qy + (y - qy) * sj
                pts.append((X, Y, zf * h * (1 + rng.uniform(-0.06, 0.04)) * dome(X, Y)))
        pts.append((ax, ay, h * dome(ax, ay)))
        pts.append((bx, by, 0.93 * h * dome(bx, by)))
    # underside: blunt rings drawn towards the whole rock's centre G, so the stones' bellies merge
    # into one rounded keel (a plausible closed shape, no detail)
    for s, zf, pull in ((0.93, -0.38, 0.08), (0.78, -0.7, 0.22), (0.52, -0.92, 0.38), (0.3, -1.0, 0.5)):
        for j in range(0, n, 2):
            x, y = fp[j]
            sj = s * (1 + rng.uniform(-0.04, 0.04))
            X, Y = cx + (x - cx) * sj, cy + (y - cy) * sj
            X, Y = X + (G[0] - X) * pull, Y + (G[1] - Y) * pull
            pts.append((X, Y, zf * D * (1 + rng.uniform(-0.06, 0.03))))
    return pts


def hull_stone(bm, pts, mat, bevel=0.32):
    """Convex hull of `pts` (sprite px) into `bm` (Blender units), dissolved into facets, chamfered."""
    sb = bmesh.new()
    vs = [sb.verts.new(((x - 24) * U, (28 - y) * U, z * U)) for x, y, z in pts]
    res = bmesh.ops.convex_hull(sb, input=vs, use_existing_faces=False)
    drop = list({g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
    if drop:
        bmesh.ops.delete(sb, geom=drop, context="VERTS")
    bmesh.ops.dissolve_limit(sb, angle_limit=math.radians(12), verts=sb.verts[:], edges=sb.edges[:])
    bmesh.ops.recalc_face_normals(sb, faces=sb.faces[:])
    sharp = [e for e in sb.edges if e.is_manifold and e.calc_face_angle(0) > math.radians(18)]
    if bevel and sharp:
        bmesh.ops.bevel(sb, geom=sharp, offset=bevel * U, offset_type="OFFSET", segments=1, profile=0.5,
                        affect="EDGES", clamp_overlap=True)
    for f in sb.faces:
        f.material_index = mat
    me = bpy.data.meshes.new("tmp")
    sb.to_mesh(me)
    sb.free()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)


def build(coll):
    idx, colors, inner = sprite()
    names, lab = labels(idx)
    spr = {"name": NAME, "colors": colors}
    mats, slot = [], {}

    def mat(i):
        if i not in slot:
            slot[i] = len(mats)
            mats.append(common.palette_material(spr, i, NAME, metallic=0.05, roughness=0.88))
        return slot[i]

    bm = bmesh.new()
    pal = {}
    cells = [(x + .5, y + .5) for y in range(H) for x in range(W) if inner[y][x]]
    G = (sum(c[0] for c in cells) / len(cells), sum(c[1] for c in cells) / len(cells))
    for i, n in enumerate(names):
        region = [[lab[y][x] == i and inner[y][x] for x in range(W)] for y in range(H)]
        if not any(map(any, region)):
            continue
        pal[n] = PAL_OVERRIDE.get(n) or region_pal(idx, colors, lab, i, inner)
        fp, outer = footprint(region, inner)
        pts = stone_points(n, fp, outer, STONES[n], G)
        hull_stone(bm, pts, mat(pal[n]), bevel=STONES[n].get("bevel", 0.32))
    print("stone palette", pal)
    LABELS.update(names=names, label=lab, pal=pal)
    obj = common.mesh_object(NAME, bm, mats, coll, smooth=False)
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
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"rock triangles {tris}")
    fmt = "AUTO"
    if "--no-bake" not in argv:  # AO bake only (maps.json "bake": "model" if a textures folder is made)
        import tempfile
        bake_maps(obj, Path(tempfile.mkdtemp(prefix="nshd45_bake_")))
        fmt = "WEBP"
    shell = common.outline_shell(obj, coll, voxel=0.02, faces=3000, smooth=6, inside=0.015)
    first = common.load_sprite(WT, PIECES[0])
    layout = [(e["model"], e["cx"] - CENTRE[0], e["cy"] - CENTRE[1]) for e in first["assemblyLayout"]]
    pieces = common.split_assembly(obj, layout)
    shells = split_open(shell, layout, coll)
    for name, cx, cy in layout:
        print(f"{name}: {sum(len(q.vertices) - 2 for q in pieces[name].data.polygons)} triangles")
    if "--review" in argv:  # the cell with the pieces placed, for render.py / measure.py
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


# --- texture: baked occlusion only (no concept projection) ---------------------------------------

def bake_maps(obj, out_dir, size=1024, samples=48):
    """AO multiplier over the palette colours (assembly-newshe-39 / usp_talon.bake_maps, trimmed):
    UV the rock, bake occlusion at two scales (the cracks darken) into a grey map, wire it in as
    Base Color = map x palette colour."""
    out_dir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
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
    bpy.ops.uv.smart_project(angle_limit=math.radians(50), island_margin=0.004, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.003)
    bpy.ops.object.mode_set(mode="OBJECT")
    img = bpy.data.images.new("nshd45B_ao", size, size, alpha=False)
    saved = {}
    for m in me.materials:
        nt = m.node_tree
        out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
        saved[m.name] = out.inputs["Surface"].links[0].from_socket
        ao_s = nt.nodes.new("ShaderNodeAmbientOcclusion")
        ao_s.samples = 16
        ao_s.inputs["Distance"].default_value = 0.14
        ao_l = nt.nodes.new("ShaderNodeAmbientOcclusion")
        ao_l.samples = 16
        ao_l.inputs["Distance"].default_value = 0.6
        sq = nt.nodes.new("ShaderNodeMath")
        sq.operation = "POWER"
        nt.links.new(ao_s.outputs["AO"], sq.inputs[0])
        sq.inputs[1].default_value = 3.0
        mul = nt.nodes.new("ShaderNodeMath")
        mul.operation = "MULTIPLY"
        nt.links.new(sq.outputs[0], mul.inputs[0])
        mix = nt.nodes.new("ShaderNodeMath")
        mix.operation = "MULTIPLY_ADD"
        nt.links.new(ao_l.outputs["AO"], mix.inputs[0])
        mix.inputs[1].default_value = 0.5
        mix.inputs[2].default_value = 0.5
        nt.links.new(mix.outputs[0], mul.inputs[1])
        lift = nt.nodes.new("ShaderNodeMath")
        lift.operation = "MULTIPLY_ADD"
        nt.links.new(mul.outputs[0], lift.inputs[0])
        lift.inputs[1].default_value = 0.75
        lift.inputs[2].default_value = 0.25
        em = nt.nodes.new("ShaderNodeEmission")
        nt.links.new(lift.outputs[0], em.inputs["Color"])
        nt.links.new(em.outputs[0], out.inputs["Surface"])
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = img
        tex.name = "bake_target"
        nt.nodes.active = tex
    bpy.ops.object.bake(type="EMIT", margin=4, use_clear=True)
    img.filepath_raw = str(out_dir / "ao.png")
    img.file_format = "PNG"
    img.save()
    for m in me.materials:
        nt = m.node_tree
        out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
        for n in list(nt.nodes):
            if n.type in ("AMBIENT_OCCLUSION", "EMISSION") or (n.type == "MATH"):
                nt.nodes.remove(n)
        nt.links.new(saved[m.name], out.inputs["Surface"])
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        tex = nt.nodes["bake_target"]
        rgb = bsdf.inputs["Base Color"].default_value[:]
        mixc = nt.nodes.new("ShaderNodeMix")
        mixc.data_type = "RGBA"
        mixc.blend_type = "MULTIPLY"
        mixc.inputs["Factor"].default_value = 1.0
        nt.links.new(tex.outputs["Color"], mixc.inputs["A"])
        mixc.inputs["B"].default_value = rgb
        nt.links.new(mixc.outputs["Result"], bsdf.inputs["Base Color"])


if __name__ == "__main__":
    main()
