"""Prototype: build a model from tools/sprite_shape.py's analysis (regions.json) plus overrides.

    blender --background --python assets/blender/proto/shape_model.py -- <name> [--overrides FILE]
            [--no-export] [--blend FILE]

<name> is a model (newsh5-47) or an assembly (assembly-newshb-115). Reads .shape/<name>/regions.json
and analysis.npz (run `python tools/sprite_shape.py <name>` first) and the overrides, by default
assets/blender/proto/overrides/<name>.json if it exists: {"model": {...}, "regions": {"r12": {...}}},
the same keys as regions.json, merged on top. The build is deterministic: the same JSON gives the
same model, so a fixer only ever edits overrides.

Each region becomes a heightfield mesh on a half-pixel grid (tools/shape_profiles.py turns the
parameters into heights) with walls down to its foot, decimated to the triangle budget, with a
pal_<index> material. An assembly is built whole and cut into pieces with common.split_assembly.
Exports to public/models/proto/<model path>.glb (the path the game uses, under proto/), which
only the model viewer's prototype switch loads; the game and src/render/spriteModels are untouched.
"""

import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1]))  # assets/blender (common)
ROOT = next(p for p in HERE.parents if (p / "package.json").exists())
sys.path.insert(0, str(ROOT / "tools"))
import common  # noqa: E402
import shape_profiles as SP  # noqa: E402

PX = 1 / 12
SMOOTH = ("round", "dome", "taper")
VERBOSE = "--verbose" in sys.argv
MIN_WALL = 1.0  # px: lower walls are left out


def args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    opts = {"name": argv[0], "overrides": None, "export": True, "blend": None}
    for i, a in enumerate(argv):
        if a == "--overrides":
            opts["overrides"] = argv[i + 1]
        elif a == "--no-export":
            opts["export"] = False
        elif a == "--blend":
            opts["blend"] = argv[i + 1]
    return opts


def load(name, overrides_path=None):
    work = ROOT / ".shape" / name
    doc = json.loads((work / "regions.json").read_text())
    npz = np.load(work / "analysis.npz")
    path = Path(overrides_path) if overrides_path else ROOT / "assets" / "blender" / "proto" / "overrides" / f"{name}.json"
    if overrides_path == "none":
        path = Path("/nonexistent")
    over = json.loads(path.read_text()) if path.exists() else {}
    regions = [{**r, **over.get("regions", {}).get(r["id"], {})} for r in doc["regions"]]
    model = {**doc.get("model", {}), **over.get("model", {})}
    unknown = set(over.get("regions", {})) - {r["id"] for r in doc["regions"]}
    if unknown:
        print(f"warning: overrides for unknown regions {sorted(unknown)}")
    return doc, regions, model, npz, (path if path.exists() else None)


def amodal(regions, shape):
    by = {r["id"]: r for r in regions}
    out = {}
    for r in regions:
        ext = [e for e in r.get("extends_under") or [] if e in by]
        if ext and r["profile"] in ("round", "taper", "dome"):
            m = np.zeros(shape, dtype=bool)
            for e in ext:
                m |= SP.region_mask(by[e], shape)
            out[r["id"]] = m
    return out


def region_mesh(name, field, mask, foot, W, H, ss, mat, smooth, drop=None, smooth_iters=3, under=None):
    """A heightfield on the region's cells (ss per px) plus walls from its edge down (or up) to
    `foot`. field: absolute z in px per cell. drop: cells (full grid) where the surface comes
    down to `foot` at its edge (round shapes meet the ground instead of standing on a rim wall).
    The outline is smoothed in XY (Laplacian along the edge, `smooth_iters` passes) so pixel
    stairs become slopes. Coordinates: origin at the sprite's centre, X right, Y up, 12 px a unit."""
    hs, ws = mask.shape
    cy, cx = np.nonzero(mask)
    acc = np.zeros((hs + 1, ws + 1))
    cnt = np.zeros((hs + 1, ws + 1))
    for dy in (0, 1):
        for dx in (0, 1):
            acc[cy + dy, cx + dx] += field[cy, cx]
            cnt[cy + dy, cx + dx] += 1
    used = cnt > 0
    vid = -np.ones((hs + 1, ws + 1), dtype=np.int64)
    vy, vx = np.nonzero(used)
    vid[vy, vx] = np.arange(len(vy))
    z = acc[vy, vx] / cnt[vy, vx]
    near = np.zeros(len(vy), dtype=bool)
    if drop is not None:
        # Corners touching a `drop` cell outside the region sit at the foot.
        pd = np.pad(drop & ~mask, 1)
        nr = pd[:-1, :-1] | pd[:-1, 1:] | pd[1:, :-1] | pd[1:, 1:]
        near = nr[vy, vx] & (cnt[vy, vx] < 4)
        z = np.where(near, foot, z)
    zu = None
    if under is not None:
        # An underside (air enemies): `under` is its z per cell, mirrored below the foot.
        au = np.zeros((hs + 1, ws + 1))
        for dy in (0, 1):
            for dx in (0, 1):
                au[cy + dy, cx + dx] += under[cy, cx]
        zu = np.where(near, foot, au[vy, vx] / cnt[vy, vx])
    xy = np.c_[vx / ss - W / 2, -(vy / ss - H / 2)].astype(float)
    faces = [(vid[y + 1, x], vid[y + 1, x + 1], vid[y, x + 1], vid[y, x]) for y, x in zip(cy, cx)]
    top_faces = len(faces)
    pad = np.pad(mask, 1)
    edges = []
    for (dy, dx), (a, b) in (((-1, 0), ((0, 0), (0, 1))), ((0, 1), ((0, 1), (1, 1))),
                             ((1, 0), ((1, 1), (1, 0))), ((0, -1), ((1, 0), (0, 0)))):
        out = mask & ~pad[1 + dy:1 + dy + hs, 1 + dx:1 + dx + ws]
        for y, x in zip(*np.nonzero(out)):
            edges.append((vid[y + a[0], x + a[1]], vid[y + b[0], x + b[1]]))
    # Smooth the outline: each edge vertex moves towards the mean of its two edge neighbours.
    nb = {}
    for ta, tb in edges:
        nb.setdefault(ta, []).append(tb)
        nb.setdefault(tb, []).append(ta)
    chain = [v for v, n in nb.items() if len(n) == 2]
    if chain:
        ci = np.array(chain)
        n0 = np.array([nb[v][0] for v in chain])
        n1 = np.array([nb[v][1] for v in chain])
        for _ in range(smooth_iters):
            xy[ci] = 0.5 * xy[ci] + 0.25 * (xy[n0] + xy[n1])
    verts = np.c_[xy * PX, z * PX]
    extra, low = [], {}
    if zu is not None:
        n = len(verts)
        verts = np.vstack([verts, np.c_[xy * PX, zu * PX]])
        faces += [(f[3] + n, f[2] + n, f[1] + n, f[0] + n) for f in faces[:top_faces]]
        for ta, tb in edges:
            if abs(z[ta] - zu[ta]) < 0.05 and abs(z[tb] - zu[tb]) < 0.05:
                continue
            faces.append((ta, tb, tb + n, ta + n))
        edges = []

    def bottom(v):
        if v not in low:
            low[v] = len(verts) + len(extra)
            extra.append((verts[v][0], verts[v][1], foot * PX))
        return low[v]

    for ta, tb in edges:
        if abs(z[ta] - foot) < MIN_WALL and abs(z[tb] - foot) < MIN_WALL:
            continue  # too low to see; leaving it out lets thin slabs decimate cleanly
        faces.append((ta, tb, bottom(tb), bottom(ta)))
    allv = np.vstack([verts, np.array(extra).reshape(-1, 3)]) if extra else verts
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(allv.tolist(), [], [tuple(int(i) for i in f) for f in faces])
    mesh.validate()
    mesh.materials.append(mat)
    for i, poly in enumerate(mesh.polygons):
        poly.use_smooth = smooth and (i < top_faces or (zu is not None and i < 2 * top_faces))
    return bpy.data.objects.new(name, mesh)


def decimate(obj, ratio, planar):
    """Planar regions: dissolve coplanar faces, and collapse only if still over twice the share
    (collapsing thin slabs pulls their tops down into spikes). Curved ones: collapse to `ratio`."""
    view = bpy.context.view_layer
    for o in view.objects:
        o.select_set(False)
    view.objects.active = obj
    obj.select_set(True)
    tris_before = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    if planar:
        m = obj.modifiers.new("planar", "DECIMATE")
        m.decimate_type = "DISSOLVE"
        m.angle_limit = math.radians(8.0)
        bpy.ops.object.modifier_apply(modifier=m.name)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    if planar and tris > 0:
        ratio = ratio * tris_before / max(tris, 1)
        if ratio > 1 / 1.3:
            ratio = 1.0
    if ratio < 1.0 and tris > 0:
        m = obj.modifiers.new("collapse", "DECIMATE")
        m.decimate_type = "COLLAPSE"
        m.ratio = max(0.01, ratio)
        bpy.ops.object.modifier_apply(modifier=m.name)
    m = obj.modifiers.new("tri", "TRIANGULATE")
    bpy.ops.object.modifier_apply(modifier=m.name)


def tri_count(obj):
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


def split_open(obj, layout, coll):
    """common.split_assembly without filling the cuts: these meshes have open edges (round tops
    meet the ground with no wall), and filling a cut that runs into them spans the whole opening.
    The pieces abut, so the cuts need no caps."""
    import bmesh
    out = {}
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)
        for co, no in (((x0 - 1, 0, 0), (-1, 0, 0)), ((x0 + 1, 0, 0), (1, 0, 0)),
                       ((0, y0 - 14 / 12, 0), (0, -1, 0)), ((0, y0 + 14 / 12, 0), (0, 1, 0))):
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no, clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        mesh = bpy.data.meshes.new(name)
        bm.to_mesh(mesh)
        bm.free()
        for mat in obj.data.materials:
            mesh.materials.append(mat)
        piece = bpy.data.objects.new(name, mesh)
        coll.objects.link(piece)
        out[name] = piece
    return out


def model_paths():
    """{(sheet, size, frame): model path} from src/render/spriteModels."""
    out = {}
    for f in (ROOT / "src" / "render" / "spriteModels").glob("*.json"):
        e = json.loads(f.read_text())
        for s in e["sprites"]:
            for fr in s["frames"]:
                out[(s["sheet"], s["size"], fr)] = e["model"]
    return out


def piece_path(piece_model, frame, paths):
    data = json.loads((ROOT / "reference" / "models" / piece_model / "sprite.json").read_text())
    s = data["sprites"][0]
    return paths.get((s["sheet"], s["size"], frame)) or json.loads(
        (ROOT / "src" / "render" / "spriteModels" / f"{piece_model}.json").read_text())["model"]


def build(name, overrides=None, export=True):
    doc, regions, model, npz, over_path = load(name, overrides)
    W, H = doc["size"]
    ss = doc["ss"]
    relief = npz["relief"]
    groups = {k: {**v, **model.get("groups", {}).get(k, {})} for k, v in doc.get("groups", {}).items()}
    bodies = SP.body_fields(regions, (H, W), groups, ss)
    solved, surface = SP.solve(regions, (H, W), ss, relief=relief, amodal=amodal(regions, (H, W)), groups=groups)
    # The heights asked for (after overrides), at each sprite pixel, for review_sheet's metrics.
    np.save(ROOT / ".shape" / name / "target_height.npy", np.nanmean(surface.reshape(H, ss, W, ss), axis=(1, 3)))
    coll = common.reset_collection(f"proto-{name}")
    sprite = {"name": name, "colors": doc["colors"]}
    mats = {}
    objs = []
    opaque = sum(r["area"] for r in regions)
    outside = ~SP.upsample(npz["idx"] >= 0, ss)
    budget = model.get("tri_budget") or int(max(500, 450 * opaque / (24 * 28)))
    for r in regions:
        if r.get("hide"):
            continue
        base, field = solved[r["id"]]
        mask = ~np.isnan(field)
        if not mask.any():
            continue
        idx = int(r.get("material", 0))
        if idx not in mats:
            mats[idx] = common.palette_material(sprite, idx, f"proto{doc['name'][-6:]}")
        foot = base if r["profile"] != "void" else 0.0
        if r["profile"] == "recess":
            foot = base  # walls rise from the recess floor to the surface round it
        # Round shapes come down to their foot at their own edge; a body's regions only at the
        # sprite's silhouette (between its regions the body surface carries on).
        if r.get("group"):
            drop = outside
        elif r["profile"] in SMOOTH:
            drop = np.ones_like(mask)
        else:
            drop = None
        under = None
        g = groups.get(r.get("group"), {})
        if g.get("below", 0) > 0 and r.get("group") in bodies:
            under = foot - float(g["below"]) * bodies[r["group"]]
        o = region_mesh(f"{name}-{r['id']}", np.nan_to_num(field), mask, foot, W, H, ss, mats[idx],
                        r["profile"] in SMOOTH or bool(r.get("group")), drop=drop, under=under)
        coll.objects.link(o)
        objs.append((r, o))
    # Triangle budget: share it by each region's raw size, at least a few per region.
    raw = {r["id"]: tri_count(o) for r, o in objs}
    total = sum(raw.values())
    for r, o in objs:
        share = max(24, budget * raw[r["id"]] / max(1, total))
        thin = r["profile"] == "recess"
        planar = r["profile"] in ("flat", "recess", "void") and not r.get("group")
        # Thin slabs only get planar dissolve: collapsing them pulls their tops into spikes.
        decimate(o, 1.0 if thin else share / max(1, raw[r["id"]]), planar=planar)
        if VERBOSE:
            print(f"  {r['id']:>4} {r['profile']:<7} raw {raw[r['id']]:6d} share {share:7.0f} -> {tri_count(o)}")
    # One object for the whole model, one material slot per palette index.
    view = bpy.context.view_layer
    for o in view.objects:
        o.select_set(False)
    for _, o in objs:
        o.select_set(True)
    view.objects.active = objs[0][1]
    bpy.ops.object.join()
    whole = view.objects.active
    whole.name = f"proto-{name}"
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=1e-5)
    bpy.ops.object.mode_set(mode="OBJECT")
    tris = tri_count(whole)
    print(f"{name}: {len(objs)} regions, {tris} triangles (budget {budget}), overrides {over_path}")
    pieces = doc["pieces"]
    exported = {}
    if export:
        paths = model_paths()
        out_root = ROOT / "public" / "models" / "proto"
        if name.startswith("assembly-"):
            layout, seen = [], set()
            for p in pieces:
                if p["model"] in seen:
                    continue
                seen.add(p["model"])
                layout.append((p["model"], p["x0"] + p["w"] / 2 - W / 2, p["y0"] + p["h"] / 2 - H / 2))
            parts = split_open(whole, layout, coll)
            for p in pieces:
                if p["model"] in exported:
                    continue
                path = piece_path(p["model"], p["frame"], paths)
                common.export_glb([parts[p["model"]]], out_root / f"{path}.glb")
                exported[p["model"]] = {"path": path, "triangles": tri_count(parts[p["model"]])}
        else:
            path = json.loads((ROOT / "src" / "render" / "spriteModels" / f"{name}.json").read_text())["model"]
            common.export_glb([whole], out_root / f"{path}.glb")
            exported[name] = {"path": path, "triangles": tris}
        # The model viewer's prototype switch reads this list (src/viewer/modelViewer.ts).
        index = sorted(str(f.relative_to(out_root).with_suffix("")) for f in out_root.rglob("*.glb"))
        (out_root / "index.json").write_text(json.dumps(index, indent=0) + "\n")
        manifest = ROOT / ".shape" / name / "build.json"
        manifest.write_text(json.dumps({"name": name, "triangles": tris, "budget": budget,
                                        "overrides": str(over_path) if over_path else None,
                                        "pieces": exported}, indent=1))
    return whole, exported


if __name__ == "__main__":
    o = args()
    build(o["name"], o["overrides"], o["export"])
    if o["blend"]:
        bpy.ops.wm.save_as_mainfile(filepath=o["blend"])
