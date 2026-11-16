"""The asteroid platforms' rock rim (shapesz.dat layer 0; DECISIONS.md D211): one tile model per rim
tile, `public/models/tiles/shapesz/rim-<tile>.glb` with `src/render/tileModels/shapesz-rim-<tile>.json`
(layer 0, which keeps its tiles: the boulders stand on their own painted tile, whose woven floor and crevices
stay the ground). The field, seams and facets are lib_rim_rock's (numpy, shared with checks outside
Blender); this script makes the meshes and exports them.

- Surface: lib_rim_rock.mesh (the rock clipped at its outline), plus walls down to just under the
  ground along the tile's edges wherever the rock reaches one (inside the neighbour's rock, so
  never seen; they only close the gap if a neighbour the maps rarely use meets a little lower).
- Look: the enemy asteroids' (lib_newshd_rock's facet ramp, D175): flat-shaded chips, each one grey
  of the tile's own ramp, matte stone. One palette material per tile (its brightest shade) with the
  chips' greys as a COLOR_0 multiplier (D209's tone), so a tile is one draw.
- Ink: the enemy asteroids' outline shell (D90's settings) made from the rock among the tile's usual
  neighbours above SHELL_FLOOR, cut open at the tile's edges and tagged `tyrian_tile_outline`, the one
  kind of tile model StructureInstances draws ink for (tiles carry none otherwise, D8).

Run: blender -b --factory-startup -P assets/blender/tiles/shapesz_rim_rock.py [-- --preview DIR]
"""

import sys
from pathlib import Path

import bmesh
import bpy

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import common  # noqa: E402
import lib_rim_rock as rr  # noqa: E402
import lib_tiles as lt  # noqa: E402

ROOT = common.repo_root(__file__)
TONE_ATTR = "rock_tone"
FINISH = {"metallic": 0.0, "roughness": 0.85}  # matte stone, as assembly-newshd-45 (D175)
#: The outline shell: D90's voxel and inside (D175's asteroids), finer, as it's cut from 3x3 tiles.
SHELL = {"voxel": 0.03, "faces": 2500, "smooth": 8, "inside": 0.004}
SHELL_FLOOR = 0.03  # units: the shell is the rock above this
EDGE_X = rr.TILE_W / 2 / 12
EDGE_Y = rr.TILE_H / 2 / 12


def on_edge(co):
    """Which tile edge a vertex lies on (None: inside)."""
    e = 1e-5
    if abs(co.x + EDGE_X) < e:
        return "L"
    if abs(co.x - EDGE_X) < e:
        return "R"
    if abs(co.y - EDGE_Y) < e:
        return "T"
    if abs(co.y + EDGE_Y) < e:
        return "B"
    return None


def build_tile(kit, n, data, coll):
    me = bpy.data.meshes.new(f"rim-{n}")
    bm = bmesh.new()
    verts = [bm.verts.new(v) for v in data["verts"]]
    faces = []
    for tri in data["tris"]:
        faces.append(bm.faces.new([verts[i] for i in tri]))
    bm.faces.ensure_lookup_table()
    n_top = len(faces)
    # walls along the tile's edges, below every boundary edge of the rock that lies on one
    low = {}

    def drop(v):
        if v not in low:
            low[v] = bm.verts.new((v.co.x, v.co.y, rr.SKIRT))
        return low[v]

    walls = []
    for e in list(bm.edges):
        if not e.is_boundary:
            continue
        a, b = e.verts
        side = on_edge(a.co)
        if side is None or side != on_edge(b.co) or max(a.co.z, b.co.z) <= 1e-6:
            continue
        # outward-facing: keep the top face's winding along the edge, reversed
        f = e.link_faces[0]
        loop = next(lp for lp in f.loops if lp.edge == e)
        p, q = loop.vert, loop.link_loop_next.vert
        walls.append(bm.faces.new([q, p, drop(p), drop(q)]))
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(f"rim-{n}", me)
    coll.objects.link(obj)
    base = data["base"]
    mat = common.material(f"pal_{base}_rim-{n}", common.srgb(*kit.colors[base]), **FINISH)
    me.materials.append(mat)
    # flat chips: every corner of a face takes its facet's normal; walls their own
    normals = []
    region, fn = data["region"], data["normals"]
    for p in me.polygons:
        nrm = tuple(fn[region[p.index]]) if p.index < n_top else tuple(p.normal)
        normals.extend([nrm] * p.loop_total)
    me.normals_split_custom_set(normals)
    # the chips' greys on COLOR_0, as multipliers of the material's palette colour
    attr = me.color_attributes.new(TONE_ATTR, "FLOAT_COLOR", "CORNER")
    dark = int(min(data["shade"]))
    for p in me.polygons:
        shade = int(data["shade"][region[p.index]]) if p.index < n_top else dark
        t = rr.tone(kit, shade, base)
        for li in p.loop_indices:
            attr.data[li].color = t
    tris = n_top + 2 * len(walls)
    print(f"rim-{n}: {n_top} rock triangles, {len(walls)} wall quads ({tris} tris), base pal_{base}, "
          f"shades {sorted(set(int(s) for s in data['shade']))}")
    return obj


def shell_source(kit, n, built, coll):
    """A closed copy of the rock of tile n among its usual neighbours (each rim tile's surface above
    SHELL_FLOOR, a floor there and walls round every open edge), for the outline shell. The floor
    is above the ground: the shell's underside, pushed out by the outline pass, must clear the
    ground's depth to draw the ink round the rock's foot (an enemy's floats over nothing)."""
    bm = bmesh.new()
    for r, row in enumerate(kit.context_tiles(n)):
        for c, t in enumerate(row):
            if t not in built:
                continue
            ox, oy = (c - 1) * 2 * EDGE_X, (1 - r) * 2 * EDGE_Y
            verts, tris = rr.mesh(built[t]["f"] - SHELL_FLOOR)
            top = [bm.verts.new((x + ox, y + oy, z + SHELL_FLOOR)) for x, y, z in verts]
            bot = [bm.verts.new((x + ox, y + oy, SHELL_FLOOR)) for x, y, _ in verts]
            edges = {}
            for a, b, cc in tris:
                bm.faces.new((top[a], top[b], top[cc]))
                bm.faces.new((bot[cc], bot[b], bot[a]))
                for p, q in ((a, b), (b, cc), (cc, a)):
                    edges[(p, q)] = edges.get((p, q), 0) + 1
            for p, q in edges:
                if (q, p) not in edges:  # an open edge of the surface: wall it down to the floor
                    bm.faces.new((top[q], top[p], bot[p], bot[q]))
    me = bpy.data.meshes.new(f"rim-{n}-closed")
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(f"rim-{n}-closed", me)
    coll.objects.link(obj)
    return obj


def shell(kit, n, built, coll):
    """The ink outline's shell (D51, D90's settings) made from the rock among its neighbours, then cut
    open at the tile's edges, so the ink runs on across a seam instead of closing round each tile
    (D211: these are the only tile models with ink; StructureInstances draws a shell tagged
    `tyrian_tile_outline`)."""
    src = shell_source(kit, n, built, coll)
    sh = common.outline_shell(src, coll, voxel=SHELL["voxel"], faces=SHELL["faces"], smooth=SHELL["smooth"],
                              inside=SHELL["inside"], islands="outer")
    bm = bmesh.new()
    bm.from_mesh(sh.data)
    lt.cut_to_tile(bm)
    bm.to_mesh(sh.data)
    bm.free()
    sh.data.shade_smooth()
    sh.name = sh.data.name = f"rim-{n}_outline"
    sh["tyrian_tile_outline"] = True
    bpy.data.objects.remove(src)
    return sh


def main():
    kit = rr.Kit(ROOT)
    ts = lt.Tileset(ROOT, "shapesz", layer=0)
    built = rr.build(kit)
    preview = lt.preview_arg()
    for n in rr.RIM_TILES:
        for o in list(bpy.data.objects):
            bpy.data.objects.remove(o)
        bpy.context.view_layer.update()  # (removed objects leave dead entries until then)
        coll = bpy.context.scene.collection
        obj = build_tile(kit, n, built[n], coll)
        sh = shell(kit, n, built, coll)
        # (layer 0 keeps its tiles by default, as the trees and boulders: no `keepTiles` key, which
        # would make it a wreck that needs a covered painting, D86)
        lt.export_tile_model(ts, [obj, sh], f"rim-{n}", 0, [[n]], color_attr=TONE_ATTR)
        if preview:
            lt.preview(ts, [obj], [[n]], str(Path(preview) / f"rim-{n}.png"))


main()
